import unittest
from scripts.run_f2_w6_b1_requalification import run
class RequalificationTests(unittest.TestCase):
    def test_inherited_suite_passes(self):
        r=run(); self.assertEqual(r['terminal'],'PASS'); self.assertEqual(r['policy_matches'],12); self.assertEqual(r['false_accepts'],0); self.assertEqual(r['false_rejects'],0)
    def test_case_ids_preserved(self): self.assertEqual([x['case_id'] for x in run()['cases']],[f'RT-{i:02d}' for i in range(1,13)])
if __name__=='__main__': unittest.main()
