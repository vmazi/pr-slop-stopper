"""Account age heuristic implementation."""

from datetime import UTC, datetime

from dateutil.relativedelta import relativedelta

from pr_slop_stopper.core.heuristics.base import BaseHeuristic, HeuristicResult, registry
from pr_slop_stopper.types import GitHubUserProtocol


class AccountAgeHeuristic(BaseHeuristic):
    """Evaluates account age to detect throwaway accounts."""

    @property
    def name(self) -> str:
        return "account_age"

    def evaluate(
        self,
        user: GitHubUserProtocol,
        *,
        reference_date: datetime | None = None,
    ) -> HeuristicResult:
        """Evaluate account age score.

        Args:
            user: GitHub user object
            reference_date: Date to calculate age from (default: now UTC)

        Returns:
            HeuristicResult with account age score
        """
        if reference_date is None:
            reference_date = datetime.now(UTC)

        created_at = user.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)

        age_delta = relativedelta(reference_date, created_at)
        age_days = (reference_date - created_at).days
        age_months = age_delta.years * 12 + age_delta.months
        age_years = age_days / 365.25

        if age_days < 30:
            score = -20
            tier = "very_new"
        elif age_days < 90:
            score = -15
            tier = "new"
        elif age_months < 6:
            score = -10
            tier = "recent"
        elif age_years < 1:
            score = 0
            tier = "neutral"
        elif age_years < 3:
            score = 5
            tier = "established"
        elif age_years < 5:
            score = 10
            tier = "mature"
        else:
            score = 15
            tier = "veteran"

        return HeuristicResult(
            name=self.name,
            score=score,
            breakdown={tier: score},
            details={
                "account_age_days": age_days,
                "account_age_months": age_months,
                "account_age_years": round(age_years, 2),
                "created_at": created_at.isoformat(),
                "tier": tier,
            },
        )


# Register the heuristic
registry.register(AccountAgeHeuristic())
