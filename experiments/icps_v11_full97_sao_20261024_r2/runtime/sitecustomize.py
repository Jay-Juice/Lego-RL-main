"""Opt-in per-process source overlay; never edits installed or production modules."""
import importlib.abc,importlib.util,json,os,pathlib,sys
if os.environ.get('ICPS_V11_OVERLAY')=='1':
    root=pathlib.Path(__file__).resolve().parent
    mapping=json.loads((root/'SOURCE_DIFF_RECEIPT.json').read_text())
    class V11Overlay(importlib.abc.MetaPathFinder):
        def find_spec(self,fullname,path=None,target=None):
            if fullname in mapping:
                return importlib.util.spec_from_file_location(fullname,root/mapping[fullname]['file'])
    sys.meta_path.insert(0,V11Overlay())
    os.environ['ICPS_V11_OVERLAY_ACTIVE']='1'
