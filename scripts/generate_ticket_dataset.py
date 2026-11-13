import csv
import random
from pathlib import Path

RANDOM_SEED = 20261113
DATASET_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "sample_tickets"
    / "fictional_classification_tickets.csv"
)

SCENARIOS: dict[str, list[tuple[str, str, str]]] = {
    "Hardware": [
        ("laptop keyboard", "has several unresponsive keys", "finish a sample spreadsheet"),
        ("external monitor", "flickers after the demo starts", "review fictional reports"),
        ("USB-C docking station", "drops connected ports intermittently", "use the sample workstation"),
        ("office printer", "repeatedly jams its paper feed", "print the demo onboarding sheet"),
        ("wired headset", "has a silent microphone during test calls", "join a fictional support meeting"),
        ("laptop battery", "loses charge while plugged in", "complete a sample task"),
    ],
    "Software": [
        ("inventory application", "closes when opening the training workspace", "review fictional stock records"),
        ("document editor", "fails to save the demo file", "finish a sample procedure"),
        ("software installer", "stops before the sample app is available", "prepare a demo workstation"),
        ("browser extension", "does not load in the training profile", "view fictional internal pages"),
        ("spreadsheet add-in", "shows an error when the sample workbook opens", "check demo calculations"),
        ("calendar client", "does not display training appointments", "prepare a fictional schedule"),
    ],
    "Network": [
        ("office Wi-Fi", "drops its connection every few minutes", "use the sample intranet"),
        ("demo VPN", "rejects a valid training connection", "reach fictional internal pages"),
        ("ethernet connection", "shows no link on the sample desk", "open the demo knowledge portal"),
        ("DNS lookup", "cannot resolve the fictional intranet hostname", "access sample network resources"),
        ("wireless access point", "has weak signal in the mock training room", "join the demo network"),
        ("network file share", "times out across the sample office link", "open fictional shared documents"),
    ],
    "Account & Access": [
        ("password reset", "does not send the sample recovery link", "sign in to the demo account"),
        ("employee account", "is locked after a fictional sign-in attempt", "access the training portal"),
        ("MFA enrollment", "does not offer the sample account registration step", "complete demo sign-in"),
        ("shared folder permission", "denies an approved sample collaborator", "open fictional project files"),
        ("single sign-on profile", "loops back to the demo login screen", "reach the sample employee portal"),
        ("role assignment", "is missing for a fictional training user", "view the allowed demo workspace"),
    ],
    "Security": [
        ("security alert", "reports a fictional suspicious sign-in", "review the mock account event"),
        ("training phishing email", "was reported from the sample inbox", "verify a fictional message"),
        ("endpoint protection status", "shows a demo device without a recent check-in", "review the mock workstation status"),
        ("browser warning", "flags a fictional unsafe training link", "record the demo investigation"),
        ("account activity notice", "shows a sample login from an unfamiliar device", "check the mock audit details"),
        ("data handling alert", "flags a fictional sample file for review", "follow the demo response checklist"),
    ],
    "Other": [
        ("time zone setting", "shows the wrong demo locale", "update a sample calendar display"),
        ("keyboard layout", "uses a different fictional language setting", "type in a demo document"),
        ("help desk question", "asks where to find the sample service catalog", "locate a fictional support form"),
        ("desk setup request", "needs a sample workstation accessory", "prepare a demo work area"),
        ("notification preference", "sends too many demo reminders", "adjust a fictional training profile"),
        ("screen brightness control", "does not save the selected demo level", "read a sample document"),
    ],
}

TITLE_TEMPLATES = (
    "Help requested: {subject}",
    "Sample report - {subject}",
    "Troubleshooting request for {subject}",
)
DESCRIPTION_TEMPLATES = (
    "{cue}. Please check {subject}: it {problem}. This is blocking the requester from {impact}.",
    "The demo request is for {cue}: {subject} {problem}. The sample user needs it to {impact}.",
    "A fictional employee describes {cue}: {subject} {problem}, preventing the task to {impact}.",
)
CATEGORY_CUES = {
    "Hardware": (
        "physical equipment support",
        "peripheral repair request",
        "workstation component issue",
    ),
    "Software": (
        "application behavior issue",
        "program installation request",
        "desktop software support",
    ),
    "Network": (
        "network connectivity issue",
        "wireless or VPN connection support",
        "internal network service problem",
    ),
    "Account & Access": (
        "user account sign-in request",
        "identity and permission issue",
        "authentication access support",
    ),
    "Security": (
        "security event review",
        "suspicious activity report",
        "endpoint protection concern",
    ),
    "Other": (
        "general IT help request",
        "workstation configuration question",
        "miscellaneous service request",
    ),
}


def generate_rows() -> list[dict[str, str]]:
    generator = random.Random(RANDOM_SEED)
    rows: list[dict[str, str]] = []
    for category, scenarios in SCENARIOS.items():
        for scenario_index, (subject, problem, impact) in enumerate(scenarios):
            group = f"{category.casefold().replace(' ', '-').replace('&', 'and')}-{scenario_index:02}"
            variants = list(range(len(TITLE_TEMPLATES)))
            generator.shuffle(variants)
            for variant in variants:
                rows.append(
                    {
                        "scenario_group": group,
                        "title": TITLE_TEMPLATES[variant].format(subject=subject),
                        "description": DESCRIPTION_TEMPLATES[variant].format(
                            cue=CATEGORY_CUES[category][variant],
                            subject=subject,
                            problem=problem,
                            impact=impact,
                        ),
                        "category": category,
                    }
                )
    generator.shuffle(rows)
    return rows


def write_dataset(path: Path = DATASET_PATH) -> int:
    rows = generate_rows()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as dataset_file:
        writer = csv.DictWriter(
            dataset_file,
            fieldnames=("scenario_group", "title", "description", "category"),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


if __name__ == "__main__":
    print(
        f"Wrote {write_dataset()} fictional labeled tickets "
        f"(seed {RANDOM_SEED}) to {DATASET_PATH}"
    )
