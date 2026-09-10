# v0.2.16
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import*


class DisputeResolver(gl.Contract):
    verdicts: TreeMap[str, str]

    def __init__(self):
        self.verdicts = TreeMap()

    @gl.public.write
    def resolve(self, dispute_id: str, role_offer: int, candidate_ask: int, reason: str) -> None:
        prompt = (
            f"Two parties disagree on a job offer. The employer offered {role_offer} "
            f"USDC/month; the candidate asked for {candidate_ask} USDC/month. "
            f"Stated reason for the dispute: {reason}. "
            f"Return a single fair settlement number in USDC/month, and nothing else."
        )
        verdict = gl.nondet.exec_prompt(prompt)
        self.verdicts[dispute_id] = verdict

    @gl.public.view
    def get_verdict(self, dispute_id: str) -> str:
        return self.verdicts.get(dispute_id, "pending")