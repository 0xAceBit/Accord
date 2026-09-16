# v0.2.16
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *


class DisputeResolver(gl.Contract):
    verdicts: TreeMap[str, u256]

    def __init__(self):
        pass

    @gl.public.write
    def resolve(
        self,
        dispute_id: str,
        role_offer: int,
        candidate_ask: int,
        reason: str
    ) -> None:

        def leader_fn():
            prompt = f"""
            Two parties disagree on a job salary.

            Employer offered: {role_offer} USDC/month.
            Candidate requested: {candidate_ask} USDC/month.
            Reason for dispute: {reason}

            Determine a fair settlement salary.

            Return ONLY a JSON object:
            {{"settlement": integer}}
            """

            return gl.nondet.exec_prompt(
                prompt,
                response_format="json"
            )

        def validator_fn(leader_result):
            if not isinstance(leader_result, gl.vm.Return):
                return False

            leader_data = leader_result.calldata

            if not isinstance(leader_data, dict):
                return False

            leader_settlement = leader_data.get("settlement")

            if not isinstance(leader_settlement, int):
                return False

            # Validator independently performs the same salary judgment.
            validator_result = leader_fn()

            if not isinstance(validator_result, dict):
                return False

            validator_settlement = validator_result.get("settlement")

            if not isinstance(validator_settlement, int):
                return False

            # Substantive consensus:
            # independent judgments may differ by at most $100.
            return abs(
                leader_settlement - validator_settlement
            ) <= 100

        result = gl.vm.run_nondet_unsafe(
            leader_fn,
            validator_fn
        )

        # Deterministic storage happens only after consensus.
        self.verdicts[dispute_id] = result["settlement"]

    @gl.public.view
    def get_verdict(self, dispute_id: str) -> u256:
        return self.verdicts.get(dispute_id, u256(0))

