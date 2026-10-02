"""PC-124: the Expo SDK every generated mobile app is on, in one place.

The store's Expo Go opens exactly one SDK - the newest (api.expo.dev/v2/versions/latest reports it as
`expoGoSdkVersion`). An app on any other SDK fails on a real phone with "Project is incompatible
with this version of Expo Go", so scanning the QR did nothing useful while the apps stayed on SDK 51.

Moving to a new SDK is a change to this file alone: the versions are the ones that SDK bundles
(expo/bundledNativeModules.json and the SDK's `relatedPackages`), so `expo install --check` is clean.
"""

from __future__ import annotations

SDK = 57

DEPENDENCIES = {
    # R-545: babel-preset-expo's output imports @babel/runtime helpers; undeclared, pnpm's strict
    # resolution cannot find them and the first bundle fails.
    "@babel/runtime": "^7.25.0",
    "@react-navigation/native": "^7.5.0",
    "@react-navigation/native-stack": "^7.20.0",
    "expo": "~57.0.26",
    "expo-constants": "~57.0.20",
    # R-591: the session token lives in the Keychain/Keystore.
    "expo-secure-store": "~57.0.4",
    "expo-status-bar": "~57.0.1",
    "lucide-react-native": "^1.50.0",
    "react": "19.2.3",
    "react-native": "0.86.3",
    "react-native-safe-area-context": "~5.7.0",
    "react-native-screens": "~4.26.0",
    "react-native-svg": "15.15.4",
}

DEV_DEPENDENCIES = {
    "@babel/core": "^7.29.0",
    # PC-101: types `process.env.EXPO_PUBLIC_*`; under pnpm it is not hoisted from Expo's own dependencies.
    "@types/node": "^20.14.0",
    "@types/react": "~19.2.4",
    # babel.config.js names it; under pnpm's strict layout a preset only Expo depends on is not found
    # ("Cannot find module 'babel-preset-expo'"), so the app declares it, as Expo's own template does.
    "babel-preset-expo": "~57.0.13",
    "typescript": "~6.0.3",
}

#: PC-121: push notifications.
PUSH = {"expo-device": "~57.0.2", "expo-notifications": "~57.0.21"}
