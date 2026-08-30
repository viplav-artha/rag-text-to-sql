COMPANY = "futwork"
SCHEMA_NAME = "portfolio"
TABLE_NAME = "futwork_vs_aop"

PROFILE = (
    "Futwork is a telecalling/voice-BPO platform that recruits and deploys a "
    "distributed gig workforce (largely home-based agents) to make outbound "
    "calls on behalf of client businesses — covering sales/lead qualification, "
    "collections, verification, customer support, and reactivation. Clients "
    "span logistics, D2C/e-commerce, fintech, and edtech (e.g. Amazon, "
    "BharatPe, Leverage, Shiprocket). Since 2024, Futwork has layered AI voice "
    "agents alongside human callers, so revenue is split in the MIS between "
    "\"HITL\" (human-in-the-loop) and \"AI + Workflows\". Clients are billed "
    "on an output/per-call basis rather than per-seat: billing_amount_<client> "
    "is the invoiced revenue from that client's call volume (INR), and "
    "minutes_spoken_<client> is the underlying call-minute activity that "
    "drives it — related but independently-tracked figures, not derived from "
    "one another. (Revenue Per Minute = billing_amount / minutes_spoken is a "
    "downstream ratio computed on demand, not a stored column.)"
)

# Columns that are dimensions/keys, not business metrics — never turned into schema chunks.
EXCLUDED_COLUMNS = frozenset({"id", "file_path", "month_name", "year"})

# Two metrics repeated per client (billing_amount_<client>, minutes_spoken_<client>).
# The ingestion script matches these by column-name prefix and fills in {client}.
PER_CLIENT_TEMPLATES = {
    "billing_amount": "Total amount invoiced to {client} in that month, in INR.",
    "minutes_spoken": "Total call minutes spoken on behalf of {client} in that month.",
}

# The ~67 genuinely distinct metrics, confirmed by the business owner.
METRIC_DESCRIPTIONS = {
    # --- AOP / target columns ---
    "aop_salary": (
        "Budgeted payroll for the operations/training/QA workforce that runs "
        "the calling operation (distinct from caller payout — this is the "
        "fixed staff who manage/train/QA the callers). INR."
    ),
    "direct_cost_aop": (
        "Budgeted gig-caller payout for the month (agent/caller compensation "
        "— cost of service delivery). INR."
    ),
    "direct_operation_cost_aop": (
        "Budgeted telecalling/domestic infrastructure cost for the month. INR."
    ),
    "ebitda_pct_targetted": "ebitda_targetted divided by total_revenue_targetted. Percent.",
    "ebitda_targetted": "Monthly EBITDA target. INR.",
    "gross_margin_pct_targetted": (
        "gross_margin_targetted divided by total_revenue_targetted. Percent."
    ),
    "gross_margin_targetted": "total_revenue_targetted minus direct_cost_aop. INR.",
    "marketing_cost_aop": "Budgeted marketing spend. INR.",
    "rent_and_utilities_aop": "Budgeted rent, utilities and staff welfare. INR.",
    "team_cost_aop": (
        "Budgeted payroll for all non-operations staff — founders, tech, "
        "sales, client success, recruitment, community, support — classified "
        "as an indirect cost. INR."
    ),
    "technology_and_saas_aop": (
        "Budgeted tech/SaaS licensing cost (per-tech-team-member license fee "
        "in this plan). INR."
    ),
    "total_direct_cost_aop": (
        "direct_cost_aop plus direct_operation_cost_aop (computed, not a "
        "source line item). INR."
    ),
    "total_indirect_cost_aop": (
        "team_cost_aop plus marketing_cost_aop plus rent_and_utilities_aop "
        "plus technology_and_saas_aop plus remaining misc overhead (payment "
        "processing, audit/accountant fees, sales licenses/travel, admin "
        "costs) — matches the 'Total Indirect Cost' row in the source model "
        "exactly. INR."
    ),
    "total_revenue_targetted": "Monthly revenue target per Futwork's AOP. INR.",
    # --- Revenue & direct costs (actuals) ---
    "total_revenue": (
        "Total revenue billed across all clients for the month. INR. "
        "Equals hitl plus ai_revenue."
    ),
    "ai_revenue": (
        "Revenue from AI-driven voice agents/workflows (no human caller "
        "involved). INR. Labeled \"AI + Workflows\" in the sheet."
    ),
    "hitl": "Revenue from human-in-the-loop calls (human callers on the platform). INR.",
    "infrastructure_cost": (
        "Total tech/infra spend to run the platform. INR. Equals server + "
        "telephony + SMS + AI-voice-processing costs."
    ),
    "server_cost_aws_searce_e2e": (
        "Cloud/server hosting cost (AWS, Searce, E2E Networks). INR. Vendor "
        "mix in this bucket shifts month to month (e.g. sometimes labeled "
        "'AWS + Google + E2E' vs 'AWS + Searce + E2E') — same underlying "
        "cost bucket regardless of vendor-name wording."
    ),
    "cloud_telephony_exotel_truecaller": (
        "Telephony/call-routing vendor cost (Exotel, TrueCaller). INR."
    ),
    "sms_infra_msg_whatsapp_truecaller": (
        "SMS/WhatsApp messaging infra cost (MSG91, WhatsApp/TrueCaller). INR."
    ),
    "ai_and_voice_processing_cost": (
        "Compute cost for AI voice/LLM processing (STT/TTS/inference). INR."
    ),
    "caller_earnings": (
        "Total amount paid out to gig callers. INR. Equals fixed_base_pay "
        "plus variable_caller_commission."
    ),
    "fixed_base_pay_weekly_monthly": "Fixed base pay to callers (weekly/monthly). INR.",
    "variable_caller_commission_monthly_bonus": "Variable pay — commission plus bonus. INR.",
    "gross_margin": (
        "Total revenue minus infrastructure_cost minus caller_earnings "
        "(sheet calls it 'Gross Profit'). INR."
    ),
    "gross_margin_pct": "gross_margin divided by total_revenue. Percent.",
    "team_cost": (
        "Total internal (non-caller) headcount cost. INR. Equals "
        "founders_salary plus team_tech_cost plus sales_client_success_team_cost "
        "plus operations_team_cost plus general_admin_team_cost."
    ),
    "founders_salary": "Founders' compensation. INR.",
    "team_tech_cost": "Tech team payroll. INR.",
    "sales_client_success_team_cost": "Sales + Client Success team payroll. INR.",
    "operations_team_cost": "Operations team payroll. INR.",
    "general_admin_team_cost": "G&A team payroll. INR.",
    "ebitda": "gross_margin minus team_cost minus other_overheads plus other_income. INR.",
    "ebitda_margin_pct": "ebitda divided by total_revenue. Percent.",
    "depreciation_and_amortization": "D&A charge for the month. INR.",
    "profit_loss_before_tax": "ebitda minus depreciation_and_amortization. INR.",
    # --- Cash & runway ---
    "funds_left": "Total liquid + invested funds remaining. INR.",
    "cash_in_hand": "Cash in bank/on hand. INR.",
    "short_term_investments_liquid_funds_short_term_fds": (
        "Liquid funds + short-term fixed deposits. INR."
    ),
    "long_term_investments_long_term_fds_bonds": (
        "Long-term fixed deposits/bonds. INR. May show no value in a given "
        "month if no long-term investments are held at that time."
    ),
    "runway_in_months": "Months of runway at current burn rate. Months.",
    # --- Clients & callers ---
    "active_clients_b2b": (
        "Active clients in the B2B/BFSI-Fintech sector bucket (also labeled "
        "'BFSI/Fintech' in some MIS versions)."
    ),
    "active_clients_edtech": "Active clients in the Edtech sector.",
    "active_clients_ecommerce_logistics": "Active clients in the Ecommerce & Logistics sector.",
    "active_clients_other_b2c": (
        "Active clients in the D2C/other-B2C sector (also labeled 'D2C/B2C')."
    ),
    "total_callers_beginning_of_the_month": "Caller headcount at month start.",
    "new_callers": "Callers onboarded during the month.",
    "churned_callers": "Callers who left during the month.",
    "total_callers_end_of_the_month": (
        "Caller headcount at month end. Equals beginning-of-month count plus "
        "new_callers minus churned_callers."
    ),
    "team_size": "Total internal (non-caller) headcount.",
    "no_of_founders": "Number of founders (a sub-line under team_size).",
    # --- Accounts receivable aging ---
    "ar_current": "Receivables not yet past due, by invoice date.",
    "ar_0_to_30_days": "Receivables 0-30 days past due.",
    "ar_30_to_60_days": "Receivables 30-60 days past due.",
    "ar_60_to_90_days": "Receivables 60-90 days past due.",
    "ar_90_plus_days": "Receivables 90+ days past due.",
    "ar_total": "Sum of all aging buckets — total outstanding receivables.",
    # --- Other overheads / indirect costs ---
    "other_overheads": (
        "Total non-payroll overhead — sum of marketing, "
        "rental_utilities_staff_welfare, travel, "
        "team_licenses_and_subscriptions, professional_fees, "
        "recruitment_cost, and others."
    ),
    "marketing": "Marketing spend.",
    "rental_utilities_staff_welfare": "Office rent, utilities, staff welfare.",
    "travel": "Travel expenses.",
    "team_licenses_and_subscriptions": "SaaS/tool licenses for the internal team.",
    "professional_fees": "Legal/audit/consulting fees.",
    "recruitment_cost": "Hiring/recruitment cost.",
    "others": "Uncategorized miscellaneous cost.",
    "other_income_including_treasury": (
        "Non-operating income — mainly treasury/interest income. Sits in the "
        "cost block positionally in the sheet, but it's income, and it's "
        "added back (not subtracted) in the EBITDA formula."
    ),
}

# NL question -> correct SQL, used to few-shot the LLM. Kept small deliberately;
# grows over time as real usage patterns emerge.
FEW_SHOT_EXAMPLES = [
    (
        "What was the total revenue in March 2026?",
        "SELECT total_revenue FROM portfolio.futwork_vs_aop "
        "WHERE year = 2026 AND month_name = 'March';",
    ),
    (
        "How does actual EBITDA compare to the AOP target for April 2026?",
        "SELECT ebitda, ebitda_targetted, ebitda - ebitda_targetted AS variance "
        "FROM portfolio.futwork_vs_aop WHERE year = 2026 AND month_name = 'April';",
    ),
    (
        "What is the split between HITL and AI revenue for May 2026?",
        "SELECT hitl, ai_revenue FROM portfolio.futwork_vs_aop "
        "WHERE year = 2026 AND month_name = 'May';",
    ),
    (
        "What was the total billing amount from Amazon in June 2026?",
        "SELECT billing_amount_amazon FROM portfolio.futwork_vs_aop "
        "WHERE year = 2026 AND month_name = 'June';",
    ),
    (
        "What is the accounts receivable aging breakdown as of June 2026?",
        "SELECT ar_current, ar_0_to_30_days, ar_30_to_60_days, ar_60_to_90_days, "
        "ar_90_plus_days, ar_total FROM portfolio.futwork_vs_aop "
        "WHERE year = 2026 AND month_name = 'June';",
    ),
]
