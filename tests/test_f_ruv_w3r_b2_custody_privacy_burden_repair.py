from __future__ import annotations
import importlib.util
from pathlib import Path
import tempfile, unittest
P=Path(__file__).resolve().parents[1]/'src/repeat_use_harness/custody_repair.py'
s=importlib.util.spec_from_file_location('m',P);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def ref(seed='a'):return {'locator':'pointer://'+seed,'identity_mode':'IMMUTABLE_CONTENT','sha256':(seed*64)[:64]}
def store(scopes):return m.store('store','subject',m.consent('subject',scopes,'2026-08-19T00:00:00Z'))
class RepairTests(unittest.TestCase):
 def term(self,code,fn):
  with self.assertRaises(m.Terminal) as c:fn()
  self.assertEqual(c.exception.code,code)
 def event(self,s,key='x'):return m.capture(s,'SOURCE_OPENED',key,{'source_ref':ref()},[ref()],'2026-08-19T00:00:00Z')
 def test_01_raw_and_unknown_fail_closed(self):
  s=store(['local_operational_capture']);self.term('NO_SAFE',lambda:m.capture(s,'SOURCE_OPENED','x',{'source_ref':ref(),'private_payload':'x'},[ref()],'2026-08-19T00:00:00Z'));self.term('NO_SAFE',lambda:m.capture(s,'CUSTOM','x',{},[ref()],'2026-08-19T00:00:00Z'))
 def test_02_purpose_scope_precedes_bytes(self):
  with tempfile.TemporaryDirectory() as td:
   d=Path(td)/'x';s=store(['local_operational_capture','artifact_export']);self.event(s);self.term('REENTRY_REQUIRED',lambda:m.export(s,d,'SHARE_OR_MERGE',['event'],'2026-08-19T01:00:00Z','e'));self.assertFalse(d.exists())
 def test_03_verify_import(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);s=store(['local_operational_capture','artifact_export']);r=self.event(s);man=m.export(s,root/'x','LOCAL_BACKUP',['event'],'2026-08-19T01:00:00Z','e');self.assertEqual(m.verify(root/'x')['bundle_digest'],man['bundle_digest']);t=store(['local_operational_capture','artifact_export']);x=m.import_bundle(root/'x',t,'2026-08-19T02:00:00Z');self.assertIn(r['record_id'],t['records']);self.assertFalse(x['consent_expanded'])
 def test_04_delete_revokes_export(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);s=store(['local_operational_capture','artifact_export']);r=self.event(s);m.export(s,root/'x','LOCAL_BACKUP',['event'],'2026-08-19T01:00:00Z','e');x=m.delete(s,[r['record_id']],'u','withdraw','2026-08-19T02:00:00Z');self.assertEqual(s['exports']['e']['state'],'REVOKED_LOCAL_HANDLE');self.assertTrue(x['export_revocation_notices'])
 def test_05_cascade(self):
  s=store(['local_operational_capture']);p=self.event(s);c=m.capture(s,'ORIENTATION_RECORDED','c',{'source_ref':ref('b')},[ref('b')],'2026-08-19T00:01:00Z',parent_ids=[p['record_id']]);x=m.delete(s,[p['record_id']],'u','x','2026-08-19T00:02:00Z');self.assertIn(c['record_id'],x['cascaded_record_ids'])
 def test_06_burden_monotone(self):
  s=store(['local_operational_capture']);m.burden_delta(s,'a',{'capture_minutes':10,'review_and_correction_minutes':5},'2026-08-19T00:00:00Z',[ref()]);m.burden_delta(s,'b',{'capture_minutes':1},'2026-08-19T00:01:00Z',[ref()]);self.assertEqual(m.burden_ledger(s)['values']['capture_minutes'],11);self.assertEqual(m.burden_terminal(s,5),'CAPTURE_COST_TOO_HIGH')
 def test_07_human_adapter_missingness(self):
  x=m.human_adapter({'usefulness_judgment':True},'B6');self.assertIsNone(x['values']['correction_reason']);self.assertFalse(x['imputed'])
 def test_08_burden_adapter_lock_in(self):
  x=m.burden_adapter({'capture_minutes':1},'B6');self.assertIsNone(x['values']['lock_in_dependence']);self.assertFalse(x['imputed'])
 def test_09_human_scope(self):
  s=store(['local_operational_capture']);self.term('REENTRY_REQUIRED',lambda:m.capture(s,'HUMAN_JUDGMENT_RECORDED','h',{'fields':{'human_usefulness_judgment':True},'human_supplied':True},[ref()],'2026-08-19T00:00:00Z',human=True))
 def test_10_retention_hold(self):
  s=store(['local_operational_capture']);m.capture(s,'SOURCE_OPENED','h',{'source_ref':ref()},[ref()],'2026-01-01T00:00:00Z',retention_hold='hold');self.assertEqual(m.retention_sweep(s,{'event':30},'2026-08-19T00:00:00Z')['terminal'],'REENTRY_REQUIRED')
 def test_11_manifest(self):
  x=m.manifest();self.assertEqual(len(x['fixed_findings']),8);self.assertFalse(x['ad_hoc_export_delete_paths'])
 def test_12_tamper(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);s=store(['local_operational_capture','artifact_export']);self.event(s);m.export(s,root/'x','LOCAL_BACKUP',['event'],'2026-08-19T01:00:00Z','e');(root/'x/payload/records.json').write_text('[]\n');self.term('NO_SAFE',lambda:m.verify(root/'x'))
if __name__=='__main__':unittest.main()
