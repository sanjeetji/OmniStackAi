# Spec: Rich Seed Data Generator (R-608)

**Tracker ID:** R-608
**Phase:** 2-3 -- Pack Framework
**Priority:** P0
**Estimated Effort:** 1 week
**Dependencies:** R-600 composer, blueprints
**Status:** Draft

---

## Domain-Aware Faker Integration

### Example: Healthcare Seeds
```python
# blueprint/seeds/healthcare.py

class HealthcareFaker:
    def patients(self, count: int = 150) -> list[Patient]:
        return [
            Patient(
                id=uuid4(),
                first_name=self.faker.first_name(),
                last_name=self.faker.last_name(),
                dob=self.faker.date_of_birth(min_age=18, max_age=90),
                gender=self.faker.random_element(["M", "F", "O"]),
                phone=self.faker.phone_number(),
                email=self.faker.email(),
                address=self.faker.street_address(),
                insurance=self.faker.insurance_provider(),
                emergency_contact=self.faker.emergency_contact(),
                medical_history=self.faker.medical_history(),
                allergies=self.faker.allergies(),
                medications=self.faker.current_medications(),
            )
            for _ in range(count)
        ]
    
    def providers(self, count: int = 20) -> list[Provider]:
        specialties = ["cardiology", "dermatology", "neurology", "orthopedics", "pediatrics"]
        return [
            Provider(
                id=uuid4(),
                first_name=self.faker.first_name(),
                last_name=self.faker.last_name(),
                specialty=self.faker.random_element(specialties),
                license_number=self.faker.medical_license(),
                npi=self.faker.npi(),
                availability=self.generate_weekly_schedule(),
                consultation_fee=self.faker.random_int(100, 500),
                languages=self.faker.random_elements(["English", "Spanish", "Mandarin"], count=2),
            )
            for _ in range(count)
        ]
    
    def appointments(self, count: int = 770, date_range: str = "-90d..+14d") -> list[Appointment]:
        states = ["completed"] * 400 + ["confirmed"] * 150 + ["requested"] * 100 + ["cancelled"] * 80 + ["no_show"] * 40
        return [
            Appointment(
                id=uuid4(),
                patient_id=self.faker.random_element(patients).id,
                provider_id=self.faker.random_element(providers).id,
                status=self.faker.random_element(states),
                scheduled_at=self.faker.date_time_between(date_range),
                duration_minutes=self.faker.random_element([15, 30, 45, 60]),
                type=self.faker.random_element(["in_clinic", "telehealth"]),
                chief_complaint=self.faker.medical_complaint() if state != "requested" else None,
            )
            for _ in range(count)
        ]
```

## Other Domain Fakers
- **Mobility**: riders, drivers, rides, vehicles, earnings
- **Commerce**: products, categories, orders, reviews, sellers
- **FinTech**: accounts, transactions, cards, loans, KYC profiles
- **Food Delivery**: restaurants, menus, orders, couriers, kitchens

## Acceptance Criteria
- [ ] Seed data passes referential integrity (FKs valid)
- [ ] Realistic distributions per domain (state ratios, date ranges)
- [ ] Faker providers for each vertical pack
- [ ] Seed generation deterministic (seeded RNG)
- [ ] Outputs SQL seed files for Supabase

## Files to Create
- services/agent-engine/src/omnistackai_agent_engine/codegen/seed_data.py
