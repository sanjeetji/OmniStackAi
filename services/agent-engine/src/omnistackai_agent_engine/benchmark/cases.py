"""PC-122: the benchmark's prompts - fixed, varied, written the way people ask.

Each case names what a correct build must contain, in the user's terms: the things it stores
(`entities`, matched loosely - "Booking" satisfies "appointment" only if the planner's own resolver
says so), the building blocks it needs (`capabilities`: workflow, ownership, money, jobs, realtime,
notifications), and how many apps the scope implies (`apps`: 1 for one app, more for an ecosystem).
These are the floor a reviewer would check first, not a full specification.

`QUICK` is a cross-section that runs in well under an hour; `FULL` is every case. Prompts are never
edited to make a run pass: a case that changes gets a new id, so runs stay comparable.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Case:
    id: str
    prompt: str
    entities: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()
    apps: int = 1
    #: The most apps the scope may have. A prompt naming two kinds of people (patients and doctors)
    #: may fairly become one app or a small ecosystem - the platform decides; a blog may not be four.
    max_apps: int | None = None
    tags: tuple[str, ...] = field(default=())

    @property
    def app_range(self) -> tuple[int, int]:
        return self.apps, self.max_apps or (self.apps if self.apps == 1 else self.apps + 3)


CASES: tuple[Case, ...] = (
    # --- marketplaces and ecosystems ---
    Case("food-delivery", "A food delivery app for my city: customers order from restaurants, restaurants accept "
         "orders, and couriers deliver them. Customers pay online and track their order live.",
         ("Restaurant", "Order", "MenuItem"), ("workflow", "money"), apps=3, tags=("ecosystem", "mobile")),
    Case("handmade-marketplace", "A marketplace for handmade jewellery where sellers list products and buyers "
         "buy them and leave reviews.", ("Product", "Order", "Review"), ("money",), apps=2, tags=("ecosystem",)),
    Case("ride-hailing", "A ride-hailing app for my city.", ("Trip",), ("workflow",), apps=2,
         tags=("ecosystem", "mobile")),
    Case("home-services", "Customers book plumbers and electricians for jobs at home and rate them afterwards.",
         ("Job", "Review"), ("workflow",), apps=2, tags=("ecosystem",)),
    Case("logistics", "A logistics app where customers book parcel shipments and track them, and drivers "
         "upload proof of delivery.", ("Shipment",), ("workflow",), apps=2, tags=("ecosystem",)),
    Case("property-rentals", "Landlords list apartments, tenants apply to rent them, and landlords approve or "
         "reject applications. Tenants pay rent monthly.", ("Property", "Application"), ("workflow",), apps=2,
         tags=("ecosystem",)),
    # --- health, education, people ---
    Case("clinic", "A clinic booking system: patients book appointments with doctors, doctors see their "
         "schedule, and patients get a reminder the day before.", ("Appointment", "Doctor"),
         ("notifications",), max_apps=3, tags=("booking",)),
    Case("online-courses", "An online course platform: instructors publish courses with lessons, students "
         "enrol, track their progress and get a certificate.", ("Course", "Lesson", "Enrollment"), (),
         max_apps=3, tags=("education",)),
    Case("school", "A school management system with classes, students, teachers, attendance and grades.",
         ("Student", "Teacher", "Attendance", "Grade"), (), max_apps=3, tags=("education",)),
    Case("gym", "A gym app: members book classes, trainers manage their class schedule, and members pay a "
         "monthly membership.", ("Class", "Booking", "Membership"), ("money",), max_apps=3, tags=("booking", "mobile")),
    Case("hr-leave", "An HR tool where employees request leave and managers approve or reject it.",
         ("LeaveRequest", "Employee"), ("workflow",), max_apps=3, tags=("internal",)),
    Case("recruiting", "A job board: companies post jobs, candidates apply with their resume, recruiters "
         "move applications through screening, interview and offer.", ("Job", "Application"),
         ("workflow",), max_apps=3, tags=("internal",)),
    # --- business software ---
    Case("crm", "A CRM for a small sales team: contacts, companies, deals in a pipeline, and tasks with due "
         "dates.", ("Contact", "Company", "Deal", "Task"), ("workflow",), tags=("saas",)),
    Case("helpdesk", "A helpdesk where customers open support tickets, agents reply and close them, and "
         "customers are notified of every reply.", ("Ticket",), ("workflow", "notifications"), max_apps=3, tags=("saas",)),
    Case("inventory", "Inventory management for a warehouse: products, stock levels per location, purchase "
         "orders to suppliers, and a low-stock report.", ("Product", "PurchaseOrder", "Supplier"), (),
         tags=("internal",)),
    Case("invoicing", "Invoicing for freelancers: clients, projects, time entries and invoices that clients "
         "pay online.", ("Client", "Invoice"), ("money",), max_apps=3, tags=("saas",)),
    Case("project-tracker", "A project management tool with projects, tasks on a board, assignees and "
         "comments, updated live for the whole team.", ("Project", "Task", "Comment"), ("realtime",),
         max_apps=3, tags=("saas",)),
    Case("restaurant-pos", "Restaurant ordering: waiters take table orders, the kitchen sees new orders live "
         "and marks them ready.", ("Order", "Table"), ("realtime", "workflow"), max_apps=3, tags=("internal",)),
    Case("subscription-saas", "A SaaS for newsletters: creators write issues, readers subscribe on paid or "
         "free plans, and issues are emailed on a schedule.", ("Issue", "Subscription"), ("money", "jobs"),
         max_apps=3, tags=("saas",)),
    Case("expense-approvals", "Employees submit expenses with a receipt photo; finance approves or rejects "
         "and pays them out.", ("Expense",), ("workflow",), max_apps=3, tags=("internal",)),
    # --- consumer ---
    Case("blog", "A simple blog with posts, categories and comments.", ("Post", "Category", "Comment"), (),
         tags=("content",)),
    Case("recipes", "A recipe sharing app where people post recipes with photos, save favourites and rate "
         "them.", ("Recipe", "Favorite", "Rating"), (), tags=("content", "mobile")),
    Case("habits", "Track my daily habits and see my streaks.", ("Habit",), (), tags=("personal", "mobile")),
    Case("budget", "A personal budget app: accounts, transactions by category, and monthly budgets with a "
         "chart of spending.", ("Transaction", "Category", "Budget"), (), tags=("personal",)),
    Case("trip-planner", "Plan a trip with friends: share an itinerary, split expenses and vote on "
         "activities.", ("Trip", "Expense", "Activity"), (), tags=("personal",)),
    Case("events", "Event ticketing: organisers create events, attendees buy tickets and get a QR code, and "
         "staff check them in at the door.", ("Event", "Ticket"), ("money",), max_apps=3, tags=("booking",)),
    Case("pet-care", "A pet care app: owners keep their pets' records, book vet visits and get vaccination "
         "reminders.", ("Pet", "Visit"), ("notifications",), max_apps=3, tags=("booking", "mobile")),
    Case("community", "A neighbourhood community app with posts, events and a marketplace for second-hand "
         "items, with chat between neighbours.", ("Post", "Event", "Message"), (), max_apps=3, tags=("social",)),
    # --- services and bookings ---
    Case("salon", "A salon booking site: clients choose a service and a stylist and book a time slot; "
         "stylists see their day.", ("Service", "Stylist", "Booking"), (), max_apps=3, tags=("booking",)),
    Case("hotel", "A small hotel booking system with rooms, rates by season, reservations and check-in.",
         ("Room", "Reservation"), ("workflow",), max_apps=3, tags=("booking",)),
    Case("car-rental", "Car rental: customers search cars by date and location, book and pay, and staff "
         "record pickup and return.", ("Car", "Booking"), ("money", "workflow"), max_apps=3, tags=("booking",)),
    Case("coworking", "A coworking space: members book desks and meeting rooms by the hour and are billed "
         "monthly.", ("Desk", "Room", "Booking"), ("money",), max_apps=3, tags=("booking",)),
    Case("laundry", "A laundry pickup service: customers schedule a pickup, drivers collect and deliver, "
         "and customers track the status.", ("Pickup",), ("workflow",), apps=2, tags=("ecosystem", "mobile")),
    # --- organisations ---
    Case("ngo-donations", "An NGO site where donors give to campaigns, see progress towards each goal and "
         "get a receipt by email.", ("Campaign", "Donation"), ("money", "notifications"), max_apps=3, tags=("content",)),
    Case("library", "A library system: books, members, loans with due dates, and overdue reminders.",
         ("Book", "Member", "Loan"), ("jobs",), max_apps=3, tags=("internal",)),
    Case("sports-league", "A sports league: teams, players, fixtures and results with a live league table.",
         ("Team", "Player", "Match"), ("realtime",), max_apps=3, tags=("content",)),
    Case("church", "A church app with sermons, events, prayer requests and giving.", ("Sermon", "Event"),
         (), max_apps=3, tags=("content", "mobile")),
    Case("real-estate", "A real estate listings site where agents list properties with photos and buyers "
         "send enquiries.", ("Property", "Enquiry"), (), max_apps=3, tags=("content",)),
    Case("maintenance", "Building maintenance: tenants report issues with photos, managers assign them to "
         "technicians, technicians close them.", ("Issue",), ("workflow", "ownership"), max_apps=3, tags=("internal",)),
    Case("podcast", "A podcast site with shows, episodes, and listeners who follow shows and comment.",
         ("Show", "Episode", "Comment"), (), max_apps=3, tags=("content",)),
)

QUICK_IDS = ("food-delivery", "clinic", "crm", "blog", "gym", "helpdesk", "recipes", "events")

SETS = {
    "quick": tuple(c for c in CASES if c.id in QUICK_IDS),
    "full": CASES,
}


def select(set_name: str = "quick", only: list[str] | None = None) -> tuple[Case, ...]:
    if only:
        wanted = set(only)
        unknown = wanted - {c.id for c in CASES}
        if unknown:
            raise ValueError(f"unknown benchmark case(s): {', '.join(sorted(unknown))}")
        return tuple(c for c in CASES if c.id in wanted)
    if set_name not in SETS:
        raise ValueError(f"unknown benchmark set {set_name!r}; one of {', '.join(SETS)}")
    return SETS[set_name]
