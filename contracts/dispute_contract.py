# v0.3.0
# { "Depends": "py-genlayer:5jycge4q8k23462jtb0b9fyey1s9qz928sz2nbrd9mg4sxqg2qng" }

import json
import genlayer as gl
from genlayer.types import *


class DisputeResolver(gl.contract.Contract):
    verdicts: gl.storage.TreeMap[str, u256]

    def __init__(self):
        pass

    @gl.public.write
    def resolve(
        self,
        dispute_id: str,
        role_offer: int,
        candidate_ask: int,
        reason: str,
    ) -> None:
        lo = min(role_offer, candidate_ask)
        hi = max(role_offer, candidate_ask)

        prompt = f"""
Two parties disagree on a job salary.

Employer offered: {role_offer} USDC/month.
Candidate requested: {candidate_ask} USDC/month.
Reason for dispute: {reason}

Determine a fair settlement salary in USDC/month.
The settlement MUST be an integer between {lo} and {hi} inclusive.

Return ONLY valid JSON in this exact format:
{{"settlement": integer}}

Do not include markdown.
Do not include ```json.
Do not include any explanation.
"""

        def leader_fn():
            raw = gl.nondet.exec_prompt(prompt)
            cleaned = str(raw).replace("```json", "").replace("```", "").strip()
            data = json.loads(cleaned)
            settlement = data["settlement"]
            if isinstance(settlement, bool) or not isinstance(settlement, int):
                raise gl.vm.UserError("settlement must be an integer")
            if settlement < lo:
                settlement = lo
            if settlement > hi:
                settlement = hi
            return settlement

        def validator_fn(leader_result):
            if not isinstance(leader_result, gl.vm.Return):
                return False
            leader_settlement = leader_result.calldata
            if not isinstance(leader_settlement, int):
                return False
            validator_settlement = leader_fn()
            return abs(leader_settlement - validator_settlement) <= 100

        result = gl.vm.run_nondet(leader_fn, validator_fn)
        self.verdicts[dispute_id] = result

    @gl.public.view
    def get_verdict(self, dispute_id: str) -> int:
        return self.verdicts.get(dispute_id, 0)