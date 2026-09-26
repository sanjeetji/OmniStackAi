# Spec: True Native Mobile (Kotlin/Compose + Swift/SwiftUI)

**Tracker ID:** R-810
**Phase:** 3 — Advanced Platform
**Priority:** P0 (Founder Hard Gate)
**Estimated Effort:** 8 weeks
**Dependencies:** R-600 (Pack Manifest), R-800 (Multi-App Architect), R-606 (Page Template Engine)
**Status:** Draft

---

## 1. Problem Statement

Native mobile (Kotlin/Jetpack Compose + Swift/SwiftUI) is a **founder hard gate** — no React Native, no Capacitor, no Flutter for this track. Engineering Mode must generate production-ready native apps per role (driver, customer, operator) with platform-idiomatic UI, native performance, and full access to device capabilities.

---

## 2. Competitive Analysis

| Feature | Emergent | Bolt | Lovable | v0 | Dyad | **OmniStackAI Target** |
|---------|----------|------|---------|-----|------|------------------------|
| Native iOS (Swift/SwiftUI) | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ **Full generation** |
| Native Android (Kotlin/Compose) | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ **Full generation** |
| React Native / Expo | ✅ | ✅ | ❌ | ❌ | Capacitor | ✅ **Also supported** |
| Flutter | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ **Optional** |
| Shared types with backend | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ **packages/shared** |
| Native device features | ❌ | Limited | ❌ | ❌ | WebView | ✅ **Full access** |
| Offline-first + sync | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ **Built-in** |
| App Store / Play Store ready | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ **Signed builds** |

---

## 3. Requirements

### 3.1 Native Mobile IR Extensions

```python
# application_ir/native_mobile.py

class NativeMobileAppIR:
    platform: 'ios' | 'android'
    language: 'swift' | 'kotlin'
    ui_framework: 'swiftui' | 'jetpack-compose'
    min_sdk: str
    target_sdk: str
    package_name: str
    bundle_id: str
    version: str
    build_number: int
    
    permissions: list[NativePermission]
    entitlements: list[Entitlement]
    features: list[DeviceFeature]
    
### 3.2 Kotlin/Compose Generator

```python
# services/agent-engine/src/omnistackai_agent_engine/codegen/native_android.py

class NativeAndroidGenerator:
    def generate(self, ir: NativeMobileAppIR, shared: SharedPackage) -> GeneratedAndroidApp:
        return GeneratedAndroidApp(
            gradle = self.generate_gradle(ir, shared),
            manifest = self.generate_manifest(ir),
            core_module = self.generate_core_module(ir, shared),
            data_module = self.generate_data_module(ir, shared),
            domain_module = self.generate_domain_module(ir, shared),
            feature_modules = self.generate_feature_modules(ir, shared),
            app_module = self.generate_app_module(ir, shared),
            camera = self.generate_camera_feature(ir) if DeviceFeature.CAMERA in ir.features else None,
            location = self.generate_location_feature(ir) if DeviceFeature.GPS in ir.features else None,
            bluetooth = self.generate_bluetooth_feature(ir) if DeviceFeature.BLUETOOTH in ir.features else None,
            biometrics = self.generate_biometrics_feature(ir) if DeviceFeature.BIOMETRICS in ir.features else None,
            background_sync = self.generate_background_sync(ir) if DeviceFeature.BACKGROUND in ir.features else None,
            push_notifications = self.generate_fcm(ir),
            room_database = self.generate_room_db(ir, shared),
            sync_engine = self.generate_sync_engine(ir, shared),
            unit_tests = self.generate_unit_tests(ir, shared),
            ui_tests = self.generate_compose_ui_tests(ir),
            integration_tests = self.generate_integration_tests(ir),
            github_actions = self.generate_ci_cd(ir),
            fastlane = self.generate_fastlane(ir),
        )
```

### 3.3 Swift/SwiftUI Generator

```python
# services/agent-engine/src/omnistackai_agent_engine/codegen/native_ios.py

class NativeIOSGenerator:
    def generate(self, ir: NativeMobileAppIR, shared: SharedPackage) -> GeneratedIOSApp:
        return GeneratedIOSApp(
            xcodeproj = self.generate_xcodeproj(ir, shared),
            package_swift = self.generate_package_swift(ir, shared),
            info_plist = self.generate_info_plist(ir),
            core_module = self.generate_core_module(ir, shared),
            data_module = self.generate_data_module(ir, shared),
            domain_module = self.generate_domain_module(ir, shared),
            feature_modules = self.generate_feature_modules(ir, shared),
            app_module = self.generate_app_module(ir, shared),
            camera = self.generate_camera_feature(ir) if DeviceFeature.CAMERA in ir.features else None,
            location = self.generate_location_feature(ir) if DeviceFeature.GPS in ir.features else None,
            bluetooth = self.generate_bluetooth_feature(ir) if DeviceFeature.BLUETOOTH in ir.features else None,
            biometrics = self.generate_face_id_touch_id(ir) if DeviceFeature.BIOMETRICS in ir.features else None,
            background_sync = self.generate_background_tasks(ir) if DeviceFeature.BACKGROUND in ir.features else None,
            push_notifications = self.generate_apns(ir),
            core_data = self.generate_core_data(ir, shared),
            sync_engine = self.generate_sync_engine(ir, shared),
            unit_tests = self.generate_unit_tests(ir, shared),
            ui_tests = self.generate_xcuitests(ir),
            integration_tests = self.generate_integration_tests(ir),
            github_actions = self.generate_ci_cd(ir),
            fastlane = self.generate_fastlane(ir),
        )
```
    architecture: 'mvi' | 'mvi-compose' | 'tca' | 'mvvm'
    dependency_injection: 'hilt' | 'koin' | 'swift-dependencies' | 'needle'
    navigation: 'compose-navigation' | 'swiftui-navigation' | 'coordinator'
    
    modules: list[NativeModule]
    shared_package: SharedPackageRef
```
### 3.4 Shared Package for Native (Kotlin + Swift)

```python
# services/agent-engine/src/omnistackai_agent_engine/codegen/shared_package_native.py

class NativeSharedPackageGenerator:
    def generate_kotlin(self, shared_ir: SharedIR) -> KotlinSharedPackage:
        return KotlinSharedPackage(
            models = self.generate_kotlin_models(shared_ir.entities, shared_ir.enums),
            api_client = self.generate_kotlin_api_client(shared_ir.api_contracts),
            dtos = self.generate_kotlin_dtos(shared_ir.api_contracts),
            state_machines = self.generate_kotlin_state_machines(shared_ir.state_machines),
            validators = self.generate_kotlin_validators(shared_ir.validators),
            formatters = self.generate_kotlin_formatters(shared_ir.formatters),
            result = self.generate_result_type(),
            coroutines = self.generate_coroutines_extensions(),
        )
    
    def generate_swift(self, shared_ir: SharedIR) -> SwiftSharedPackage:
        return SwiftSharedPackage(
            models = self.generate_swift_models(shared_ir.entities, shared_ir.enums),
            api_client = self.generate_swift_api_client(shared_ir.api_contracts),
            dtos = self.generate_swift_dtos(shared_ir.api_contracts),
            state_machines = self.generate_swift_state_machines(shared_ir.state_machines),
            validators = self.generate_swift_validators(shared_ir.validators),
            formatters = self.generate_swift_formatters(shared_ir.formatters),
            async_result = self.generate_async_result(),
            combine_extensions = self.generate_combine_extensions(),
        )
```

### 3.5 Role-Specific Native Apps

| Role | Android Features | iOS Features |
|------|------------------|--------------|
| **Driver** | GPS tracking (foreground service), Camera (docs), Bluetooth (beacon), Biometrics (login), Background sync (location), Push (FCM) | CoreLocation (background), Camera, Bluetooth (CoreBluetooth), FaceID/TouchID, BackgroundTasks, Push (APNs) |
| **Customer** | Camera (photos), Biometrics, Push, Location (places) | Camera, FaceID/TouchID, Push, MapKit/Places |
| **Operator** | Camera (incidents), GPS (dispatch), Bluetooth (fleet), Push, Background | Camera, GPS, Bluetooth, Push, BackgroundTasks |

---

## 4. Acceptance Criteria

| ID | Criterion | Verification |
|----|-----------|--------------|
| AC-01 | Kotlin/Compose app builds with `./gradlew assembleRelease` | Build test |
| AC-02 | Swift/SwiftUI app builds with `xcodebuild` | Build test |
| AC-03 | Shared types compile in both Kotlin + Swift | Cross-compile test |
| AC-04 | API client works against generated backend | Integration test |
| AC-05 | Native features work (camera, GPS, biometrics, push) | Device test |
| AC-06 | Offline-first sync works (create offline → sync online) | E2E test |
| AC-07 | App Store / Play Store build passes validation | Store submission test |
| AC-08 | Role-specific apps generated from same IR | Multi-app test |
| AC-09 | Shared package versioned + published to local Maven / SwiftPM | Publish test |

---

## 5. Implementation Tasks

| Task ID | Description | Owner | Estimate |
|---------|-------------|-------|----------|
| R-810.1 | NativeMobileAppIR schema + validation | AI Engineer | 5 days |
| R-810.2 | Kotlin/Compose generator (core + features) | Mobile Engineer | 15 days |
| R-810.3 | Swift/SwiftUI generator (core + features) | Mobile Engineer | 15 days |
| R-810.4 | Shared package generator (Kotlin + Swift) | AI Engineer | 10 days |
| R-810.5 | Native feature modules | Mobile Engineer | 15 days |
| R-810.6 | Offline-first sync engine | Mobile Engineer | 10 days |
| R-810.7 | CI/CD + Fastlane for both platforms | Platform | 5 days |
| R-810.8 | Integration with Multi-App Architect | AI Engineer | 5 days |

---

## 6. Files to Create

- `application_ir/native_mobile.py`
- `services/agent-engine/src/omnistackai_agent_engine/codegen/native_android.py`
- `services/agent-engine/src/omnistackai_agent_engine/codegen/native_ios.py`
- `services/agent-engine/src/omnistackai_agent_engine/codegen/shared_package_native.py`
- `services/agent-engine/src/omnistackai_agent_engine/codegen/native_features/`
- `services/agent-engine/src/omnistackai_agent_engine/codegen/offline_sync/`
- `templates/native/android/`
- `templates/native/ios/`
- `apps/console-web/app/studio/engineering/native-mobile-config.tsx`

---

## 7. Definition of Done

- [ ] Both generators produce compiling, testable projects
- [ ] Shared types work end-to-end
- [ ] 3 role-specific native apps generate correctly
- [ ] All native features functional on device
- [ ] Offline-first sync verified
- [ ] Store-ready builds produced
- [ ] Integrated in Engineering Mode Multi-App Architect
- [ ] Documentation: native patterns, platform differences, testing guide