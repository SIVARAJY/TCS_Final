"""Deterministic investigator knowledge: how strong each signal is, its innocent explanation, how to verify it."""
KB = {
    "shared_device": ("strong", "Customers may be family members or colleagues using one computer or phone.", "Confirm whether the customers are related and who owns the device.", "Review the ownership and login history of the shared device."),
    "shared_ip": ("moderate", "A shared home, office, café or mobile carrier gateway can produce one IP for unrelated people.", "Check IP type (residential vs. VPN/proxy/carrier NAT) and time overlap of logins.", "Compare login timestamps across the customers on the shared IP."),
    "same_entity": ("strong", "A data-entry variant or a re-registration of one genuine customer.", "Compare KYC documents (ID number, photo) for both records.", "Verify identity documents; merge or flag duplicate customer records."),
    "fan_in": ("strong", "Family pooling money, rent collection, payroll, or a small business receiving customer payments.", "Check the relationship and stated purpose of each payment to the beneficiary.", "Examine the beneficiary's full transaction history and onboarding purpose."),
    "pass_through": ("moderate", "A payment aggregator, agent or business account legitimately forwards what it receives.", "Check if the account type and declared business justify high forwarding.", "Review the account's historical in/out pattern for the same behaviour."),
    "rapid_movement": ("strong", "An automated sweep or scheduled payout can also move funds within minutes.", "Check whether the account has a standing instruction or automated payout.", "Trace where the forwarded funds went next and whether they were cashed out."),
    "circular_flow": ("moderate", "Reimbursements, bill splitting or loans between friends can create loops.", "Ask for the purpose of each transfer and the relationship between the account holders.", "Check whether similar circular patterns occurred previously on these accounts."),
    "anomaly": ("moderate", "A one-off legitimate event (property sale, insurance payout, bonus) can look unusual.", "Ask for supporting documents for the unusual amount.", "Compare the account against its own earlier activity and customer profile."),
}
GENERIC_STEPS = ["Review customer complaints and existing alerts for the entities involved.",
                 "Decision stays with a human investigator: this tool recommends, it does not conclude."]
POINTS = {"strong": 20, "moderate": 10, "weak": 3}


def strength_of(f):
    base = KB[f["type"]][0]
    if f.get("benign"):
        return "weak"
    return base
