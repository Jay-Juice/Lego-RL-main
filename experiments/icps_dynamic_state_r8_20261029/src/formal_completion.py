"""Full-horizon success check. No stop/save/approval logic at step20."""
import json
import os
from pathlib import Path


def verify_complete(config):
    checkpoint = Path(os.environ['ICPS_CHECKPOINT_ROOT'])
    assert (checkpoint / 'latest_checkpointed_iteration.txt').read_text().strip() == '97'
    folder = checkpoint / 'global_step_97'
    manifest = json.loads((folder / 'PI_COMPLETE.json').read_text())
    assert manifest['global_step'] == 97
    assert manifest['experiment'] == config.trainer.experiment_name
    assert manifest['world_size'] == 8
    assert len(manifest['files']) == 49
    for name, entry in manifest['files'].items():
        size = entry['size'] if isinstance(entry, dict) else entry
        assert (folder / name).stat().st_size == size and size > 0
    from formal_checkpoint import verify_resume_metadata
    metadata = verify_resume_metadata(folder, config, 97)
    return dict(status='FULL97_COMPLETED', completed_step=97,
                checkpoint=str(folder), resume_metadata=metadata,
                native_model_optimizer_save_contract=True,
                bitwise_restore_tested=False)
