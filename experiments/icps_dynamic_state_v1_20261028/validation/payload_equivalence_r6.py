"""Compare persisted PI payloads, excluding only old S1 elapsed telemetry."""
import copy,math

def semantic_payload(payload):
    result=copy.deepcopy(payload)
    for key in ['wall_seconds','CPU_seconds']:
        value=result['serialized']['S1'].pop(key)
        assert isinstance(value,(int,float)) and not isinstance(value,bool)
        assert math.isfinite(value) and value>=0
    return result

def assert_equivalent(old,current):
    assert semantic_payload(old)==semantic_payload(current), 'PI payload drift beyond S1 elapsed telemetry'
