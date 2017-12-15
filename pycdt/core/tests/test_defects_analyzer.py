# coding: utf-8

from __future__ import division

__author__ = "Bharat Medasani"
__copyright__ = "Copyright 2014, The Materials Project"
__version__ = "1.0"
__maintainer__ = "Bharat Medasani"
__email__ = "mbkumar@gmail.com"
__status__ = "Development"
__date__ = "May 6, 2015"

import os
import unittest

from monty.serialization import loadfn, dumpfn
from monty.json import MontyDecoder, MontyEncoder
from monty.tempfile import ScratchDir
from pymatgen.core.sites import PeriodicSite
from pymatgen.core.lattice import Lattice
from pymatgen.entries.computed_entries import ComputedStructureEntry
from pycdt.core.defects_analyzer import ComputedDefect, DefectsAnalyzer

file_loc = os.path.join('..', '..', '..', 'test_files')

class ComputedDefectTest(unittest.TestCase):
    def setUp(self):
        entry_file = os.path.join(file_loc, 'vac_cr2o3_struct_entry.json')
        entry = loadfn(entry_file, cls=MontyDecoder)
        lattice = Lattice([[9.995004137201189, -2.1469568e-08, 0.0],
                           [-4.997501105922451, 8.655927903729987, 0.0],
                           [0.0, 0.0, 13.67956098598296]])
        coords = [0.1666665000000016, 0.3333334999999984, 0.014505185117094302]
        site_in_bulk = PeriodicSite('Cr', coords, lattice)
        multiplicity = 12
        supercell_size = [2, 2, 1]
        q = -2
        q_corr =  0.98716
        o_corr = 0.39139821874799996
        name = "vac_1_Cr"
        self.com_def = ComputedDefect(
            entry, site_in_bulk, multiplicity, supercell_size, q, q_corr,
            o_corr, name)

    def test_as_from_dict(self):
        d = self.com_def.as_dict()
        comp_def = ComputedDefect.from_dict(d)
        self.assertIsInstance(comp_def, ComputedDefect)
        with ScratchDir('.'):
            dumpfn(self.com_def, 'tmp.json', cls=MontyEncoder)
            comp_def = loadfn('tmp.json', cls=MontyDecoder)
            self.assertIsInstance(comp_def, ComputedDefect)


class DefectsAnalyzerTest(unittest.TestCase):
    def setUp(self):
        blk_entry_file = os.path.join(file_loc, 'Cr2O3_defects.json')
        blk_entry = loadfn(blk_entry_file, cls=MontyDecoder)
        bulk_struct = blk_entry['bulk']['supercell']['structure']
        bulk_energy = -100
        bulk_entry = ComputedStructureEntry(bulk_struct, bulk_energy)
        e_vbm = 0.5
        mu_elts = {'Cr': -10, 'O': -5}
        bandgap = 3.0
        self.da = DefectsAnalyzer(bulk_entry, e_vbm, mu_elts, bandgap)

        d1_entry_file = os.path.join(file_loc, 'Cr2O3_defects.json')
        d1_entry = loadfn(d1_entry_file, cls=MontyDecoder)
        structure = d1_entry['vacancies'][0]['supercell']['structure']
        site_in_bulk = d1_entry['vacancies'][0]['bulk_supercell_site']
        mult = d1_entry['vacancies'][0]['site_multiplicity']
        sc_size = d1_entry['vacancies'][0]['supercell']['size']
        entry_defect = ComputedStructureEntry( structure, -99)
        self.cd = ComputedDefect(entry_defect, site_in_bulk, multiplicity=mult,
                                 supercell_size=sc_size, charge=2, name='vac_1_Cr')


        entry_defect2 = ComputedStructureEntry( structure, -99)
        self.cd2 = ComputedDefect(entry_defect2, site_in_bulk, multiplicity=mult,
                                 supercell_size=sc_size, charge=1, name='vac_1_Cr')

    def test_as_from_dict(self):
        d = self.da.as_dict()
        da = DefectsAnalyzer.from_dict(d)
        self.assertIsInstance(da, DefectsAnalyzer)
        with ScratchDir('.'):
            dumpfn(self.da, 'tmp.json', cls=MontyEncoder)
            da = loadfn('tmp.json', cls=MontyDecoder)
            self.assertIsInstance(da, DefectsAnalyzer)

    def test_add_computed_defect(self):
        self.da.add_computed_defect(self.cd)
        self.assertEqual( len(self.da._defects), 1)
        self.assertEqual( self.da._formation_energies[0], -3.)


    def test_change_charge_correction(self):
        self.da.add_computed_defect(self.cd)
        self.assertEqual( self.da._defects[0].charge_correction, 0.)
        self.da.change_charge_correction( 0, -1.)
        self.assertEqual( self.da._defects[0].charge_correction, -1.)
        self.assertEqual( self.da._formation_energies[0], -4.)

    def test_change_other_correction(self):
        self.da.add_computed_defect(self.cd)
        self.assertEqual( self.da._defects[0].other_correction, 0.)
        self.da.change_other_correction( 0, -1.5)
        self.assertEqual( self.da._defects[0].other_correction, -1.5)
        self.assertEqual( self.da._formation_energies[0], -4.5)

    def test_get_all_defect_types(self):
        self.da.add_computed_defect(self.cd)
        self.assertArrayEqual( self.da._get_all_defect_types(), ['vac_1_Cr'])

    def test_compute_form_en(self):
        self.da.add_computed_defect(self.cd)
        self.assertEqual( self.da._formation_energies[0], -3.)

    def test_correct_bg_simple(self):
        self.assertEqual( self.da._e_vbm, 0.5)
        self.assertEqual( self.da._band_gap, 3.0)
        self.da.correct_bg_simple( 0.3, 0.5)
        self.assertEqual( self.da._e_vbm, 0.2)
        self.assertEqual( self.da._band_gap, 3.8)
        self.da.add_computed_defect(self.cd)
        self.assertEqual( self.da._formation_energies[0], -3.6)

    def test_get_transition_levels(self):
        self.da.add_computed_defect(self.cd)
        self.da.add_computed_defect(self.cd2)
        self.assertEqual(self.da.get_transition_levels()['vac_1_Cr'].keys(), [(1, 2)])
        self.assertEqual(self.da.get_transition_levels()['vac_1_Cr'][(1, 2)], -0.5)

    def test_get_form_energy(self):
        self.da.add_computed_defect(self.cd)
        self.assertEqual( self.da._get_form_energy(0.5, 0), -2.)

    def test_get_formation_energies(self):
        self.da.add_computed_defect(self.cd)
        self.da.add_computed_defect(self.cd2)
        list_fe = self.da.get_formation_energies(ef = 0.5)
        self.assertArrayEqual( [list_fe[0]['energy'], list_fe[1]['energy']] , [-2., -3.])

    def test_get_defects_concentration(self):
        self.da.add_computed_defect(self.cd)
        self.da.add_computed_defect(self.cd2)
        list_c = self.da.get_defects_concentration(temp=300., ef=0.5)
        self.assertArrayEqual( [list_c[0]['conc'], list_c[1]['conc']] ,
                               [2.3075483087087652e+62, 1.453493521232979e+79])
        list_c = self.da.get_defects_concentration(temp=1000., ef=0.5)
        self.assertArrayEqual( [list_c[0]['conc'], list_c[1]['conc']] ,
                               [6.9852762150255027e+38, 7.6553010344336244e+43])

    def test_get_defects_concentration_old(self):
        self.da.add_computed_defect(self.cd)
        self.da.add_computed_defect(self.cd2)
        list_c = self.da.get_defects_concentration(temp=300., ef=0.5)
        self.assertArrayEqual( [list_c[0]['conc'], list_c[1]['conc']] ,
                               [2.3075483087087652e+62, 1.453493521232979e+79])
        list_c = self.da.get_defects_concentration(temp=1000., ef=0.5)
        self.assertArrayEqual( [list_c[0]['conc'], list_c[1]['conc']] ,
                               [6.9852762150255027e+38, 7.6553010344336244e+43])

    def test_get_dos(self):
        dosval = self.da._get_dos(-1., 2., 3., 4., -1.4)
        self.assertEqual( dosval, 1.5568745675641716e+45)

    def test_get_dos_fd_elec(self):
        elecval = self.da._get_dos_fd_elec(3.1, 2.9, 300., 2., 3., 4.)
        self.assertEqual( elecval, 9.300000567970405e+24)

    def test_get_dos_fd_hole(self):
        holeval = self.da._get_dos_fd_hole(-0.1, 0.2, 300., 2., 3., 4.)
        self.assertEqual( holeval, 1.9442064601243644e+23)

    def test_get_qd(self):
        self.da.add_computed_defect(self.cd)
        self.da.add_computed_defect(self.cd2)
        val = self.da._get_qd( 0.5, 300.)
        self.assertEqual( val, 1.453493521232979e+79)

    def test_get_qi(self):
        val = self.da.get_qi(0.1, 300., [1., 2., 3.], [ 4., 5., 6.])
        self.assertEqual( val, 1.151292510656441e+25)

    def test_get_qtot(self):
        self.da.add_computed_defect(self.cd)
        self.da.add_computed_defect(self.cd2)
        val = self.da._get_qtot(0.1, 300., [1., 2., 3.], [ 4., 5., 6.])
        self.assertEqual( val, 7.6228613357589505e+85)

    def test_get_eq_ef(self): #no unittest until re-organization with real dos integration is available
        pass

    def test_get_non_eq_ef(self): #no unittest until re-organization with real dos integration is available
        pass

    def test_get_non_eq_qd(self): #no unittest until re-organization with real dos integration is available
        pass

    def test_get_non_eq_conc(self): #no unittest until re-organization with real dos integration is available
        pass

    def test_get_non_eq_qtot(self): #no unittest until re-organization with real dos integration is available
        pass

    def test_correct_bg(self): #deprecated
        pass

    def test_get_defect_occupancies(self): #deprecated
        pass



if __name__ == '__main__':
    import unittest
    unittest.main()
