from __future__ import annotations
import json, subprocess, sys, tempfile, unittest
from pathlib import Path
SCRIPT=Path(__file__).resolve().parents[1]/'scripts'/'run_interpersonal_exchange_witness.py'
class TestExchange(unittest.TestCase):
    def test_two_process_positive_and_negative(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); result=json.loads(subprocess.run([sys.executable,str(SCRIPT),'all',str(root/'work'),str(root/'out')],check=True,capture_output=True,text=True).stdout)
            self.assertTrue(result['passed'])
            pos=json.loads((root/'out'/'b.json').read_text()); neg=json.loads((root/'out'/'b-invalid.json').read_text())
            self.assertEqual(pos['disposition'],'COMPOSED_AND_ADAPTED')
            self.assertFalse(pos['canonical_source_migrated']); self.assertFalse(pos['hosted_network_used'])
            self.assertEqual(neg['disposition'],'FAILED_CLOSED'); self.assertIn('version',neg['failed_gates'])
if __name__=='__main__': unittest.main()
