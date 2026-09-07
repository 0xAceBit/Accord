# { "Seq": [] }
from genlayer import *


class DisputeCourt(gl.Contract):
    """Minimal dispute contract for a role and two salary positions."""

    def __init__(self):
        pass

    @gl.public.view
    def resolve_dispute(
        self,
        role: str,
        salary_offered: int,
        salary_expected: int,
    ) -> str:
        if salary_offered == salary_expected:
            return f"{role}: terms aligned at {salary_offered} USDC/month."

        verdict = round((salary_offered + salary_expected) / 2)
        return (
            f"{role}: settle at {verdict} USDC/month "
            f"between the offered {salary_offered} and expected {salary_expected}."
        )
