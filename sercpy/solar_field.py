# -*- coding: utf-8 -*-
"""
Created on Thu Sep 24 09:42:44 2026

@author: Adrian Riebel Brummer
"""



class Solar_Field( ):
    def __init__(
            
            self,
            *,
            
            coll_area,
            coll_n0,
            coll_a1,
            coll_a2,
            coll_IAM,
            coll_test_flow_per_m2,
            test_fluid_props,
            coll_tilt,
            coll_azimuth,
            coll_rows,
            colls_per_row,
            row_mode,
            steam_mode,
            fluid_props,
            non_shadeable_rows,
            collector_model_name,
            tolerance = 1e-3,
            max_iterations = 100):
        
        
        assert coll_a1 > 0
        self.coll_area = coll_area
        self.coll_n0 = coll_n0
        self.coll_a1 = coll_a1
        self.coll_a2 = coll_a2
        self.collector_model_name = collector_model_name
        if coll_test_flow_per_m2 is not None and test_fluid_props is not None:
            self.correct_flow = True
            if coll_test_flow_per_m2 == 0:
                coll_test_flow = 0.02*coll_area
            else:
                coll_test_flow = coll_test_flow_per_m2*coll_area
            if type(test_fluid_props) == float or type(test_fluid_props) == int:
                test_fluid_cp = test_fluid_props
            else:
                test_fluid_cp = test_fluid_props.liquid_spec_heat
            self.FpUL = -(coll_test_flow*test_fluid_cp/coll_area)*log(1 - coll_a1*coll_area/(coll_test_flow*test_fluid_cp))
            self.test_conditions = (coll_test_flow*test_fluid_cp/(coll_area*self.FpUL))*(1 - exp( - coll_area*self.FpUL/(coll_test_flow*test_fluid_cp)))
        else:
            self.correct_flow = False
        assert type( coll_rows ) == int and type( colls_per_row ) == int
        assert type( non_shadeable_rows ) == int and non_shadeable_rows >= 0 and non_shadeable_rows <= coll_rows
        assert row_mode in ['series', 'parallel']
        if row_mode == 'series':
            self.shadeable_rows = coll_rows - non_shadeable_rows
            self.non_shadeable_rows = non_shadeable_rows
            self.colls_per_row = colls_per_row
        if row_mode == 'parallel':
            self.shadeable_rows = (coll_rows - non_shadeable_rows)*colls_per_row
            self.non_shadeable_rows = non_shadeable_rows*colls_per_row
            self.colls_per_row = 1
        self.coll_rows = self.shadeable_rows + self.non_shadeable_rows
        self.fluid_props = fluid_props
        assert steam_mode in ['purgar_vapor', 'no_purgar_vapor']
        self.steam_mode = steam_mode
        self.tolerance = tolerance
        self.max_iterations = max_iterations
    
    def h_out_coll(self, m_in, h_in, irradiance, IAM_eff, T_amb, flow_correction_factor):
        '''
        Function that computes the specific enthalpy of the flow leaving an individual collector.
        It considers the flow temperature and the ambient temperature in order to estimate the efficiency of the collector.

        Parameters:
            - m_in: mass flow entering the collector (kg/hr)
            - h_in: specific enthalpy of the flow entering the collector (kJ/kg)
            - irradiance: solar radiation reaching the collector ( kJ / ( hr * m^2 ) )
            - T_amb: ambient temperature (°C)

        Returns:
            - specific enthalpy of the flow leaving the collector.
        '''
        T_in = self.fluid_props.h_to_T(h_in)
        eff = self.coll_n0*IAM_eff - self.coll_a1*(T_in - T_amb)/irradiance - self.coll_a2*(T_in - T_amb)*abs(T_in - T_amb)/irradiance
        if eff < 0:
            eff = 0
        eff = flow_correction_factor*eff
        power = eff*irradiance*self.coll_area
        return h_in + power/m_in


    def h_out_row(self, m_in_row, h_in_row, h_mains, irradiance, IAM_eff, T_amb, flow_correction_factor):
        '''
        Function that computes the specific enthalpy of the flow leaving a row of collectors.

        Parameters:
            - m_in_row: mass flow entering the row (kg/hr)
            - h_in_row: specific enthalpy of the flow entering the row (kJ/kg)
            - h_mains: specific enthalpy of the mains flow that will be introduced into the field in the case that vapor is generated inside the collectors (kJ/kg).
            - irradiance: solar irradiance reaching the collector row ( kJ / ( hr * m^2 ) )
            - T_amb: ambient temperature (°C)

        Returns a tuple with the following elements:
            - specific enthalpy of the flow leaving the row (kJ/kg)
            - power being "wasted" (only when vapor is generated) to heat the mains flow that is introduced to compensate the vapor loss. This flow is heated from its initial enthalpy to the specific enthalpy of vapor at saturation (kJ/hr).
            - vapor mass flow being released (or mains water flow being introduced to compensate the vapor loss) (kg/hr)
            - number of iterations executed to achieve convergence (no units)
            - a boolean value which is True if the maximal number of allowed iterations was reached without achieving convergence, and False otherwise.
        '''
        
        if self.steam_mode == 'no_purgar_vapor':
            m_in = m_in_row
            h_in = h_in_row
            for i in range(self.colls_per_row):
                h_in = self.h_out_coll(m_in, h_in, irradiance, IAM_eff, T_amb, flow_correction_factor)
            h_out = h_in
            return h_out, 0, 0, 0, False
        
        if self.steam_mode == 'purgar_vapor':
            
            m_mains = 0
            it = 0
            while True:
                m_in = m_in_row + m_mains
                h_in = (m_in_row*h_in_row + m_mains*h_mains)/m_in
                for i in range(self.colls_per_row):
                    h_in = self.h_out_coll(m_in, h_in, irradiance, IAM_eff, T_amb, flow_correction_factor)
                h_out = h_in
                m_vap = self.fluid_props.quality(h_out)*m_in
                it = it+1
                if m_mains == m_vap or abs(m_mains - m_vap)/max([ m_mains, m_vap ]) < self.tolerance:
                    maxIt = False
                    break
                if it == self.max_iterations:
                    maxIt = True
                    break
                Q_useful = m_in_row*(self.fluid_props.h_sat_liq - h_in_row)
                Q_actual = m_in*(h_out - (m_in_row*h_in_row + m_mains*h_mains)/m_in)
                Q_waste = Q_actual - Q_useful
                m_mains = Q_waste/(self.fluid_props.h_sat_vap - h_mains)
            if m_vap > 0:
                if m_in_row == 0:
                    h_out = h_in_row
                else:
                    h_out = self.fluid_props.h_sat_liq
                return h_out, m_vap*(self.fluid_props.h_sat_vap - h_mains), m_vap, it, maxIt
            else:
                return h_out, 0, 0, it, maxIt
            
    def compute_outputs(self, inputs):
        '''
        Function that computes the specific enthalpy of the flow that is leaving the solar field.

        Parameters:
            - m_in_field: mass flow entering the solar field (kg/hr).
            - h_in_field: specific enthalpy of the flow entering the solar field (kJ/kg).
            - h_mains: specific enthalpy of the mains flow that will be introduced into the field in the case that vapor is generated inside the collectors (kJ/kg).
            - irradiance: solar irradiance reaching the solar field ( kJ / ( hr * m^2 ) )
            - T_amb: ambient temperature (°C)

        Returns a dictionary with the following keys:
            - 'h_out': specific enthalpy of the flow leaving the tank (kJ/kg)
            - 'Q_useful': useful energy delivered to the flow (i.e. all energy which is not used to generate vapor) (kJ/hr)
            - 'Q_waste': wasted energy which is used to generate vapor inside the collectors (kJ/hr)
            - 'm_vap': mass flow of vapor being released from the field. (kg/hr)
            - 'efficiency': Efficiency of the solar field, defined as Q_useful divided by the result of the irradiance multiplied by the total area of the solar field
            - 'iterations': number of iterations that were necessary to achieve convergence between the introduced mains flow and the vapor flow being released (no units)
            - 'maxIt': boolean value which is True if the maximum number of allowed iterations was reached without achieving convergence.
        '''
        m_in_field = inputs[0]
        h_in_field = inputs[1]
        irradiance_first_row = inputs[2]
        irradiance_shadeable_rows = inputs[3]
        IAM_first_row = inputs[4]
        IAM_shadeable_rows = inputs[5]
        T_amb = inputs[6]
        if self.steam_mode == 'purgar_vapor':
            T_mains = inputs[7]
            h_mains = self.fluid_props.T_to_h(T_mains)
        else:
            h_mains = None
        
        if m_in_field <= 0:
            self.outputs = { 'outlet_h': {'output_type': 'h', 'value': h_in_field},
                             'outlet_flowrate': {'output_type': 'flowrate', 'value': m_in_field},
                             'useful_power': {'output_type': 'power', 'value': 0},
                             'wasted_power': {'output_type': 'power', 'value': 0},
                             'steam_flowrate': {'output_type': 'flowrate', 'value': 0},
                             'efficiency': {'output_type': 'ratio', 'value': None},
                             'iterations': {'output_type': 'int', 'value': 0},
                             'maxIt': {'output_type': 'bool', 'value': False} }
            return
        
        m_in_rows = m_in_field/( self.shadeable_rows + self.non_shadeable_rows  )
        
        if self.correct_flow:
            use_conditions = ( m_in_rows*self.fluid_props.liquid_spec_heat/(self.coll_area*self.FpUL) )*( 1 - exp( - self.coll_area*self.FpUL/( m_in_rows*self.fluid_props.liquid_spec_heat ) ) )
            flow_correction_factor = use_conditions/self.test_conditions
        else:
            flow_correction_factor = 1
            
        if irradiance_first_row > 0:
            h_out_non_shadeable_rows, Q_waste_non_shadeable_rows, m_waste_non_shadeable_rows, it_non_shadeable_rows, maxIt_non_shadeable_rows = self.h_out_row(m_in_rows, h_in_field, h_mains, irradiance_first_row, IAM_first_row, T_amb, flow_correction_factor)
        else:
            h_out_non_shadeable_rows = h_in_field
            Q_waste_non_shadeable_rows = 0
            m_waste_non_shadeable_rows = 0
            it_non_shadeable_rows = 1
            maxIt_non_shadeable_rows = False
        if irradiance_shadeable_rows > 0:
            h_out_shadeable_rows, Q_waste_shadeable_rows, m_waste_shadeable_rows, it_shadeable_rows, maxIt_shadeable_rows = self.h_out_row(m_in_rows, h_in_field, h_mains, irradiance_shadeable_rows, IAM_shadeable_rows, T_amb, flow_correction_factor)
        else:
            h_out_shadeable_rows = h_in_field
            Q_waste_shadeable_rows = 0
            m_waste_shadeable_rows = 0
            it_shadeable_rows = 1
            maxIt_shadeable_rows = False
            
        h_out = ( h_out_non_shadeable_rows*self.non_shadeable_rows + h_out_shadeable_rows*self.shadeable_rows )/self.coll_rows
        Q_waste = Q_waste_non_shadeable_rows*self.non_shadeable_rows + Q_waste_shadeable_rows*self.shadeable_rows
        Q_useful = m_in_field*(h_out - h_in_field)
        m_waste = m_waste_non_shadeable_rows*self.non_shadeable_rows + m_waste_shadeable_rows*self.shadeable_rows
        if irradiance_first_row <= 0:
            efficiency = None
        else:
            efficiency = Q_useful/( irradiance_first_row*self.coll_area*self.coll_rows*self.colls_per_row )
        
        it = it_non_shadeable_rows + it_shadeable_rows
        maxIt = maxIt_non_shadeable_rows or maxIt_shadeable_rows
        
        self.outputs = { 'outlet_h': {'output_type': 'h', 'value': h_out},
                         'outlet_flowrate': {'output_type': 'flowrate', 'value': m_in_field},
                         'useful_power': {'output_type': 'power', 'value': Q_useful},
                         'wasted_power': {'output_type': 'power', 'value': Q_waste},
                         'steam_flowrate': {'output_type': 'flowrate', 'value': m_waste},
                         'efficiency': {'output_type': 'ratio', 'value': efficiency},
                         'iterations': {'output_type': 'int', 'value': it},
                         'maxIt': {'output_type': 'bool', 'value': maxIt} }

# class Solar_Field( Device ):
#     def __init__(self, coll_area, coll_n0, coll_a1, coll_a2, coll_test_flow_per_m2, test_fluid_props,
#                  coll_tilt, coll_azimuth, coll_rows, colls_per_row, row_mode, steam_mode, fluid_props,
#                  non_shadeable_rows, collector_model_name, tolerance = 1e-3, max_iterations = 100):
#         super().__init__()
#         assert coll_a1 > 0
#         self.coll_area = coll_area
#         self.coll_n0 = coll_n0
#         self.coll_a1 = coll_a1
#         self.coll_a2 = coll_a2
#         self.collector_model_name = collector_model_name
#         if coll_test_flow_per_m2 is not None and test_fluid_props is not None:
#             self.correct_flow = True
#             if coll_test_flow_per_m2 == 0:
#                 coll_test_flow = 0.02*coll_area
#             else:
#                 coll_test_flow = coll_test_flow_per_m2*coll_area
#             if type(test_fluid_props) == float or type(test_fluid_props) == int:
#                 test_fluid_cp = test_fluid_props
#             else:
#                 test_fluid_cp = test_fluid_props.liquid_spec_heat
#             self.FpUL = -(coll_test_flow*test_fluid_cp/coll_area)*log(1 - coll_a1*coll_area/(coll_test_flow*test_fluid_cp))
#             self.test_conditions = (coll_test_flow*test_fluid_cp/(coll_area*self.FpUL))*(1 - exp( - coll_area*self.FpUL/(coll_test_flow*test_fluid_cp)))
#         else:
#             self.correct_flow = False
#         assert type( coll_rows ) == int and type( colls_per_row ) == int
#         assert type( non_shadeable_rows ) == int and non_shadeable_rows >= 0 and non_shadeable_rows <= coll_rows
#         assert row_mode in ['series', 'parallel']
#         if row_mode == 'series':
#             self.shadeable_rows = coll_rows - non_shadeable_rows
#             self.non_shadeable_rows = non_shadeable_rows
#             self.colls_per_row = colls_per_row
#         if row_mode == 'parallel':
#             self.shadeable_rows = (coll_rows - non_shadeable_rows)*colls_per_row
#             self.non_shadeable_rows = non_shadeable_rows*colls_per_row
#             self.colls_per_row = 1
#         self.coll_rows = self.shadeable_rows + self.non_shadeable_rows
#         self.fluid_props = fluid_props
#         assert steam_mode in ['purgar_vapor', 'no_purgar_vapor']
#         self.steam_mode = steam_mode
#         self.tolerance = tolerance
#         self.max_iterations = max_iterations
    
#     def h_out_coll(self, m_in, h_in, irradiance, IAM_eff, T_amb, flow_correction_factor):
#         '''
#         Function that computes the specific enthalpy of the flow leaving an individual collector.
#         It considers the flow temperature and the ambient temperature in order to estimate the efficiency of the collector.

#         Parameters:
#             - m_in: mass flow entering the collector (kg/hr)
#             - h_in: specific enthalpy of the flow entering the collector (kJ/kg)
#             - irradiance: solar radiation reaching the collector ( kJ / ( hr * m^2 ) )
#             - T_amb: ambient temperature (°C)

#         Returns:
#             - specific enthalpy of the flow leaving the collector.
#         '''
#         T_in = self.fluid_props.h_to_T(h_in)
#         eff = self.coll_n0*IAM_eff - self.coll_a1*(T_in - T_amb)/irradiance - self.coll_a2*(T_in - T_amb)*abs(T_in - T_amb)/irradiance
#         if eff < 0:
#             eff = 0
#         eff = flow_correction_factor*eff
#         power = eff*irradiance*self.coll_area
#         return h_in + power/m_in


#     def h_out_row(self, m_in_row, h_in_row, h_mains, irradiance, IAM_eff, T_amb, flow_correction_factor):
#         '''
#         Function that computes the specific enthalpy of the flow leaving a row of collectors.

#         Parameters:
#             - m_in_row: mass flow entering the row (kg/hr)
#             - h_in_row: specific enthalpy of the flow entering the row (kJ/kg)
#             - h_mains: specific enthalpy of the mains flow that will be introduced into the field in the case that vapor is generated inside the collectors (kJ/kg).
#             - irradiance: solar irradiance reaching the collector row ( kJ / ( hr * m^2 ) )
#             - T_amb: ambient temperature (°C)

#         Returns a tuple with the following elements:
#             - specific enthalpy of the flow leaving the row (kJ/kg)
#             - power being "wasted" (only when vapor is generated) to heat the mains flow that is introduced to compensate the vapor loss. This flow is heated from its initial enthalpy to the specific enthalpy of vapor at saturation (kJ/hr).
#             - vapor mass flow being released (or mains water flow being introduced to compensate the vapor loss) (kg/hr)
#             - number of iterations executed to achieve convergence (no units)
#             - a boolean value which is True if the maximal number of allowed iterations was reached without achieving convergence, and False otherwise.
#         '''
        
#         if self.steam_mode == 'no_purgar_vapor':
#             m_in = m_in_row
#             h_in = h_in_row
#             for i in range(self.colls_per_row):
#                 h_in = self.h_out_coll(m_in, h_in, irradiance, IAM_eff, T_amb, flow_correction_factor)
#             h_out = h_in
#             return h_out, 0, 0, 0, False
        
#         if self.steam_mode == 'purgar_vapor':
            
#             m_mains = 0
#             it = 0
#             while True:
#                 m_in = m_in_row + m_mains
#                 h_in = (m_in_row*h_in_row + m_mains*h_mains)/m_in
#                 for i in range(self.colls_per_row):
#                     h_in = self.h_out_coll(m_in, h_in, irradiance, IAM_eff, T_amb, flow_correction_factor)
#                 h_out = h_in
#                 m_vap = self.fluid_props.quality(h_out)*m_in
#                 it = it+1
#                 if m_mains == m_vap or abs(m_mains - m_vap)/max([ m_mains, m_vap ]) < self.tolerance:
#                     maxIt = False
#                     break
#                 if it == self.max_iterations:
#                     maxIt = True
#                     break
#                 Q_useful = m_in_row*(self.fluid_props.h_sat_liq - h_in_row)
#                 Q_actual = m_in*(h_out - (m_in_row*h_in_row + m_mains*h_mains)/m_in)
#                 Q_waste = Q_actual - Q_useful
#                 m_mains = Q_waste/(self.fluid_props.h_sat_vap - h_mains)
#             if m_vap > 0:
#                 if m_in_row == 0:
#                     h_out = h_in_row
#                 else:
#                     h_out = self.fluid_props.h_sat_liq
#                 return h_out, m_vap*(self.fluid_props.h_sat_vap - h_mains), m_vap, it, maxIt
#             else:
#                 return h_out, 0, 0, it, maxIt
            
#     def compute_outputs(self, inputs):
#         '''
#         Function that computes the specific enthalpy of the flow that is leaving the solar field.

#         Parameters:
#             - m_in_field: mass flow entering the solar field (kg/hr).
#             - h_in_field: specific enthalpy of the flow entering the solar field (kJ/kg).
#             - h_mains: specific enthalpy of the mains flow that will be introduced into the field in the case that vapor is generated inside the collectors (kJ/kg).
#             - irradiance: solar irradiance reaching the solar field ( kJ / ( hr * m^2 ) )
#             - T_amb: ambient temperature (°C)

#         Returns a dictionary with the following keys:
#             - 'h_out': specific enthalpy of the flow leaving the tank (kJ/kg)
#             - 'Q_useful': useful energy delivered to the flow (i.e. all energy which is not used to generate vapor) (kJ/hr)
#             - 'Q_waste': wasted energy which is used to generate vapor inside the collectors (kJ/hr)
#             - 'm_vap': mass flow of vapor being released from the field. (kg/hr)
#             - 'efficiency': Efficiency of the solar field, defined as Q_useful divided by the result of the irradiance multiplied by the total area of the solar field
#             - 'iterations': number of iterations that were necessary to achieve convergence between the introduced mains flow and the vapor flow being released (no units)
#             - 'maxIt': boolean value which is True if the maximum number of allowed iterations was reached without achieving convergence.
#         '''
#         m_in_field = inputs[0]
#         h_in_field = inputs[1]
#         irradiance_first_row = inputs[2]
#         irradiance_shadeable_rows = inputs[3]
#         IAM_first_row = inputs[4]
#         IAM_shadeable_rows = inputs[5]
#         T_amb = inputs[6]
#         if self.steam_mode == 'purgar_vapor':
#             T_mains = inputs[7]
#             h_mains = self.fluid_props.T_to_h(T_mains)
#         else:
#             h_mains = None
        
#         if m_in_field <= 0:
#             self.outputs = { 'outlet_h': {'output_type': 'h', 'value': h_in_field},
#                              'outlet_flowrate': {'output_type': 'flowrate', 'value': m_in_field},
#                              'useful_power': {'output_type': 'power', 'value': 0},
#                              'wasted_power': {'output_type': 'power', 'value': 0},
#                              'steam_flowrate': {'output_type': 'flowrate', 'value': 0},
#                              'efficiency': {'output_type': 'ratio', 'value': None},
#                              'iterations': {'output_type': 'int', 'value': 0},
#                              'maxIt': {'output_type': 'bool', 'value': False} }
#             return
        
#         m_in_rows = m_in_field/( self.shadeable_rows + self.non_shadeable_rows  )
        
#         if self.correct_flow:
#             use_conditions = ( m_in_rows*self.fluid_props.liquid_spec_heat/(self.coll_area*self.FpUL) )*( 1 - exp( - self.coll_area*self.FpUL/( m_in_rows*self.fluid_props.liquid_spec_heat ) ) )
#             flow_correction_factor = use_conditions/self.test_conditions
#         else:
#             flow_correction_factor = 1
            
#         if irradiance_first_row > 0:
#             h_out_non_shadeable_rows, Q_waste_non_shadeable_rows, m_waste_non_shadeable_rows, it_non_shadeable_rows, maxIt_non_shadeable_rows = self.h_out_row(m_in_rows, h_in_field, h_mains, irradiance_first_row, IAM_first_row, T_amb, flow_correction_factor)
#         else:
#             h_out_non_shadeable_rows = h_in_field
#             Q_waste_non_shadeable_rows = 0
#             m_waste_non_shadeable_rows = 0
#             it_non_shadeable_rows = 1
#             maxIt_non_shadeable_rows = False
#         if irradiance_shadeable_rows > 0:
#             h_out_shadeable_rows, Q_waste_shadeable_rows, m_waste_shadeable_rows, it_shadeable_rows, maxIt_shadeable_rows = self.h_out_row(m_in_rows, h_in_field, h_mains, irradiance_shadeable_rows, IAM_shadeable_rows, T_amb, flow_correction_factor)
#         else:
#             h_out_shadeable_rows = h_in_field
#             Q_waste_shadeable_rows = 0
#             m_waste_shadeable_rows = 0
#             it_shadeable_rows = 1
#             maxIt_shadeable_rows = False
            
#         h_out = ( h_out_non_shadeable_rows*self.non_shadeable_rows + h_out_shadeable_rows*self.shadeable_rows )/self.coll_rows
#         Q_waste = Q_waste_non_shadeable_rows*self.non_shadeable_rows + Q_waste_shadeable_rows*self.shadeable_rows
#         Q_useful = m_in_field*(h_out - h_in_field)
#         m_waste = m_waste_non_shadeable_rows*self.non_shadeable_rows + m_waste_shadeable_rows*self.shadeable_rows
#         if irradiance_first_row <= 0:
#             efficiency = None
#         else:
#             efficiency = Q_useful/( irradiance_first_row*self.coll_area*self.coll_rows*self.colls_per_row )
        
#         it = it_non_shadeable_rows + it_shadeable_rows
#         maxIt = maxIt_non_shadeable_rows or maxIt_shadeable_rows
        
#         self.outputs = { 'outlet_h': {'output_type': 'h', 'value': h_out},
#                          'outlet_flowrate': {'output_type': 'flowrate', 'value': m_in_field},
#                          'useful_power': {'output_type': 'power', 'value': Q_useful},
#                          'wasted_power': {'output_type': 'power', 'value': Q_waste},
#                          'steam_flowrate': {'output_type': 'flowrate', 'value': m_waste},
#                          'efficiency': {'output_type': 'ratio', 'value': efficiency},
#                          'iterations': {'output_type': 'int', 'value': it},
#                          'maxIt': {'output_type': 'bool', 'value': maxIt} }