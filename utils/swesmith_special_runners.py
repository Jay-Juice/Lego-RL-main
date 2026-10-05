"""Task-local compatibility retained from the previously validated AL adapter."""
import json

MODIN_ENV = {
    'MODIN_CPUS': '2', 'MODIN_GPUS': '0', 'MODIN_MEMORY': '536870912',
    'NUMEXPR_MAX_THREADS': '2', 'RAY_num_server_call_thread': '2',
    'RAY_gcs_server_rpc_server_thread_num': '2',
    'RAY_gcs_server_rpc_client_thread_num': '2',
}

# Use Tornado's native runner, including its logging and warning checks. Only
# the report format changes. Like pytest, an exception raised while executing a
# test body is a failed test; setup/teardown/loader errors remain unresolved.
TORNADO = r'''import json, sys, unittest, xml.etree.ElementTree as ET
root = ET.Element('testsuite')
report = sys.argv[2]
class RecordingResult(unittest.TextTestResult):
    def record(self, test, status=None, detail=''):
        module, cls, method = test.id().rsplit('.', 2)
        case = ET.SubElement(root, 'testcase', classname=module+'.'+cls, name=method)
        if status: ET.SubElement(case, status).text = detail
    def addSuccess(self, test):
        super().addSuccess(test); self.record(test)
    def addFailure(self, test, error):
        super().addFailure(test, error); self.record(test, 'failure', self._exc_info_to_string(error,test))
    def addError(self, test, error):
        super().addError(test, error)
        method = getattr(test, getattr(test, '_testMethodName', ''), None)
        code = getattr(getattr(method, '__func__', method), '__code__', None)
        trace = error[2]
        in_body = False
        while trace is not None:
            in_body = in_body or (code is not None and trace.tb_frame.f_code is code)
            trace = trace.tb_next
        self.record(test, 'failure' if in_body else 'error', self._exc_info_to_string(error,test))
    def addSkip(self, test, reason):
        super().addSkip(test, reason); self.record(test, 'skipped', reason)
    def addExpectedFailure(self, test, error):
        super().addExpectedFailure(test,error); self.record(test,'skipped','expected failure')
    def addUnexpectedSuccess(self,test):
        super().addUnexpectedSuccess(test); self.record(test,'failure','unexpected success')
unittest.TextTestResult = RecordingResult
sys.argv = ['tornado-tests', '--verbose', *json.loads(sys.argv[1])]
try:
    from tornado.test.runtests import main
    main()
finally:
    ET.ElementTree(root).write(report, encoding='utf-8', xml_declaration=True)
'''


def adapt(config, nodes, command, env, report):
    iid = config['instance_id']
    if iid.startswith('modin-project__modin.'):
        env.update(MODIN_ENV)
        if '-n' in command:
            command[command.index('-n') + 1] = '0'
    if iid.startswith('jd__tenacity.'):
        ordered = sorted(nodes, key=lambda node: node.split('::', 1)[0])
        assert command[-len(nodes):] == nodes
        command[-len(nodes):] = ordered
    if iid.startswith('tornadoweb__tornado.'):
        native = []
        for node in nodes:
            path, cls, method = node.split('::')
            if not path.endswith('.py'):
                raise ValueError('Invalid Tornado test node')
            native.append(path[:-3].replace('/', '.') + '.' + cls + '.' + method)
        command = [command[0], '-c', TORNADO, json.dumps(native), str(report)]
    return command, env
