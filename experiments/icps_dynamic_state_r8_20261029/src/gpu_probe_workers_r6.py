"""Probe-only subclasses add one read-only ONE_TO_ALL audit; native methods inherited."""
from verl.single_controller.base.decorator import Dispatch, register
from verl.workers.engine_workers import ActorRolloutRefWorker, TrainingWorker
from gpu_rank_audit_r6 import engine_audit


class AuditedCriticWorker(TrainingWorker):
    @register(dispatch_mode=Dispatch.ONE_TO_ALL)
    def r6_rank_audit(self, stage):
        return engine_audit(self, 'critic', stage)


class AuditedActorWorker(ActorRolloutRefWorker):
    @register(dispatch_mode=Dispatch.ONE_TO_ALL)
    def r6_rank_audit(self, stage):
        return engine_audit(self.actor, 'actor', stage)
