"""React Native / Expo framework adapter (Section 37 and 6.4 of Brief v6).

Generates a complete, production-grade, TypeScript-first React Native / Expo application
as a `GeneratedProject`. Pure and deterministic — nothing is installed or run here.
Assembled under `apps/mobile/` within the customer monorepo when `ir.project_strategy.mobile_profile`
is set to `MobileProfile.REACT_NATIVE`.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

from ..application_ir import ApplicationIR, Entity, FieldType, MobileProfile
from .auth_guard import needs_auth
from .auth_templates import RN_AUTH_CONTEXT, RN_AUTH_SCREENS
from .adapter import GenerationTarget
from .files import GeneratedFile, GeneratedProject
from .brand_project import app_config_js
from .mobile_release import bundle_identifier, release_files

if TYPE_CHECKING:
    from collections.abc import Iterable


def _slug(name: str) -> str:
    """Generate a clean URL/package slug from a display name."""
    cleaned = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return cleaned or "app"


def _to_pascal(name: str) -> str:
    """Convert snake_case or dash-case to PascalCase."""
    parts = re.split(r"[^a-zA-Z0-9]+", name)
    return "".join(part.capitalize() for part in parts if part)


def _to_snake(name: str) -> str:
    """Convert any string to snake_case."""
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", name).strip("_").lower()
    return cleaned or "item"


def _ts_field_type(ft: FieldType) -> str:
    match ft:
        case FieldType.INT | FieldType.FLOAT:
            return "number"
        case FieldType.BOOL:
            return "boolean"
        case FieldType.JSON:
            return "Record<string, unknown>"
        case _:
            return "string"


class ReactNativeAdapter:
    """Framework adapter generating a production-grade React Native (Expo) app."""

    @property
    def target(self) -> GenerationTarget:
        return GenerationTarget.REACT_NATIVE

    def generate(self, ir: ApplicationIR) -> GeneratedProject:
        files: list[GeneratedFile] = []
        slug = _slug(ir.name)

        # 1. Project Configuration Files
        files.append(self._generate_package_json(slug))
        # R-548: Expo's dynamic config, reading the repo's brand.json. A static app.json
        # would silently win-or-lose against it and leave a user with no way to tell why.
        files.append(app_config_js())
        files.append(self._generate_tsconfig())
        files.append(self._generate_babel_config())
        files.append(self._generate_index_js())

        # 2. Design System Tokens & Components
        files.append(self._generate_tokens(ir))
        files.append(self._generate_button_component())
        files.append(self._generate_card_component())
        files.append(self._generate_badge_component())
        files.append(self._generate_input_component())
        files.append(self._generate_stat_card_component())
        files.append(self._generate_screen_container())

        # 3. Shared API & Auth Layer
        files.append(self._generate_api_client())
        files.append(self._generate_auth_context(ir))
        if needs_auth(ir):
            files.append(GeneratedFile("src/app/screens/AuthScreens.tsx", RN_AUTH_SCREENS))

        # 4. Per-Entity Features (Model, API, Hook, Screens)
        for entity in ir.entities:
            files.extend(self._generate_entity_feature(entity, ir))

        # 5. App Root & Navigation
        files.append(self._generate_overview_screen(ir))
        files.append(self._generate_root_navigator(ir))
        files.append(self._generate_app_root(ir))

        # 6. Store release (R-546): eas.json, brand-coloured icons, the iOS privacy manifest,
        # listing metadata, a CI workflow and the publish guide. No credential is created, used or
        # embedded — every secret is referenced by name so the publisher supplies it later.
        files.extend(release_files(ir, _slug(ir.name), bundle_identifier(_slug(ir.name))))

        return GeneratedProject(self.target.value, files)

    # ── Configurations ─────────────────────────────────────────────────────────

    def _generate_package_json(self, slug: str) -> GeneratedFile:
        manifest = {
            "name": f"{slug}-mobile",
            "version": "1.0.0",
            "main": "index.js",
            "scripts": {
                "start": "expo start",
                "android": "expo start --android",
                "ios": "expo start --ios",
                "web": "expo start --web",
            },
            "dependencies": {
                # R-545: babel-preset-expo transpiles through @babel/plugin-transform-runtime,
                # whose output imports @babel/runtime helpers at runtime. Undeclared, pnpm's
                # strict resolution cannot find them and the very first bundle fails with
                # "Unable to resolve module @babel/runtime/helpers/interopRequireDefault" —
                # the app never opened on a phone.
                "@babel/runtime": "^7.25.0",
                "@react-navigation/native": "^6.1.18",
                "@react-navigation/native-stack": "^6.10.1",
                "expo": "~51.0.0",
                "expo-constants": "~16.0.2",
                # R-591: the session token lives in the Keychain/Keystore. Pinned to the version
                # Expo SDK 51 bundles (expo/packages/expo/bundledNativeModules.json).
                "expo-secure-store": "~13.0.2",
                "expo-status-bar": "~1.12.1",
                "lucide-react-native": "^0.453.0",
                "react": "18.2.0",
                "react-native": "0.74.5",
                "react-native-safe-area-context": "4.10.5",
                "react-native-screens": "3.31.1",
                "react-native-svg": "15.2.0",
            },
            "devDependencies": {
                "@babel/core": "^7.20.0",
                "@types/react": "~18.2.45",
                "typescript": "~5.3.3",
            },
            "private": True,
        }
        return GeneratedFile("package.json", json.dumps(manifest, indent=2) + "\n")

    def _generate_tsconfig(self) -> GeneratedFile:
        content = json.dumps(
            {
                "extends": "expo/tsconfig.base",
                "compilerOptions": {
                    "strict": True,
                },
            },
            indent=2,
        ) + "\n"
        return GeneratedFile("tsconfig.json", content)

    def _generate_babel_config(self) -> GeneratedFile:
        content = (
            "module.exports = function (api) {\n"
            "  api.cache(true);\n"
            "  return {\n"
            "    presets: ['babel-preset-expo'],\n"
            "  };\n"
            "};\n"
        )
        return GeneratedFile("babel.config.js", content)

    def _generate_index_js(self) -> GeneratedFile:
        content = (
            "import { registerRootComponent } from 'expo';\n"
            "import App from './src/app/App';\n\n"
            "registerRootComponent(App);\n"
        )
        return GeneratedFile("index.js", content)

    # ── Design System ──────────────────────────────────────────────────────────

    def _generate_tokens(self, ir: ApplicationIR) -> GeneratedFile:
        primary = ir.brand.primary_color
        primary_dark = ir.brand.dark_primary_color
        content = (
            "// Brand design tokens matching OmniStackAI design system\n"
            "export const tokens = {\n"
            "  colors: {\n"
            f'    primary: "{primary}",\n'
            f'    primaryDark: "{primary_dark}",\n'
            '    primaryMuted: "rgba(99, 102, 241, 0.15)",\n'
            '    background: "#090d16",\n'
            '    surface: "#111827",\n'
            '    surfaceSubtle: "#1f2937",\n'
            '    card: "#141c2e",\n'
            '    text: "#f9fafb",\n'
            '    textMuted: "#9ca3af",\n'
            '    border: "#1f293d",\n'
            '    borderLight: "#374151",\n'
            '    success: "#10b981",\n'
            '    successBg: "rgba(16, 185, 129, 0.12)",\n'
            '    warning: "#f59e0b",\n'
            '    warningBg: "rgba(245, 158, 11, 0.12)",\n'
            '    danger: "#ef4444",\n'
            '    dangerBg: "rgba(239, 68, 68, 0.12)",\n'
            '    info: "#3b82f6",\n'
            "  },\n"
            "  radii: {\n"
            "    sm: 6,\n"
            "    md: 10,\n"
            "    lg: 14,\n"
            "    xl: 20,\n"
            "    full: 9999,\n"
            "  },\n"
            "  spacing: {\n"
            "    xs: 4,\n"
            "    sm: 8,\n"
            "    md: 16,\n"
            "    lg: 24,\n"
            "    xl: 32,\n"
            "  },\n"
            "  fontSize: {\n"
            "    xs: 11,\n"
            "    sm: 13,\n"
            "    md: 15,\n"
            "    lg: 18,\n"
            "    xl: 22,\n"
            "    xxl: 28,\n"
            "  },\n"
            "};\n"
        )
        return GeneratedFile("src/design-system/tokens.ts", content)

    def _generate_button_component(self) -> GeneratedFile:
        content = (
            "import React from 'react';\n"
            "import {\n"
            "  TouchableOpacity,\n"
            "  Text,\n"
            "  StyleSheet,\n"
            "  ActivityIndicator,\n"
            "  TouchableOpacityProps,\n"
            "} from 'react-native';\n"
            "import { tokens } from '../tokens';\n\n"
            "export interface ButtonProps extends TouchableOpacityProps {\n"
            "  title: string;\n"
            "  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';\n"
            "  size?: 'sm' | 'md' | 'lg';\n"
            "  loading?: boolean;\n"
            "}\n\n"
            "export const Button: React.FC<ButtonProps> = ({\n"
            "  title,\n"
            "  variant = 'primary',\n"
            "  size = 'md',\n"
            "  loading = false,\n"
            "  disabled,\n"
            "  style,\n"
            "  ...rest\n"
            "}) => {\n"
            "  const isInteractive = !disabled && !loading;\n"
            "  return (\n"
            "    <TouchableOpacity\n"
            "      style={[\n"
            "        styles.base,\n"
            "        styles[variant],\n"
            "        sizeStyles[size],\n"
            "        !isInteractive && styles.disabled,\n"
            "        style,\n"
            "      ]}\n"
            "      disabled={!isInteractive}\n"
            "      activeOpacity={0.75}\n"
            "      {...rest}\n"
            "    >\n"
            "      {loading ? (\n"
            "        <ActivityIndicator\n"
            "          color={variant === 'outline' || variant === 'ghost' ? tokens.colors.primary : '#fff'}\n"
            "          size=\"small\"\n"
            "        />\n"
            "      ) : (\n"
            "        <Text\n"
            "          style={[\n"
            "            styles.text,\n"
            "            textVariants[variant],\n"
            "            textSizeStyles[size],\n"
            "          ]}\n"
            "        >\n"
            "          {title}\n"
            "        </Text>\n"
            "      )}\n"
            "    </TouchableOpacity>\n"
            "  );\n"
            "};\n\n"
            "const styles = StyleSheet.create({\n"
            "  base: {\n"
            "    borderRadius: tokens.radii.md,\n"
            "    alignItems: 'center',\n"
            "    justifyContent: 'center',\n"
            "    flexDirection: 'row',\n"
            "  },\n"
            "  primary: {\n"
            "    backgroundColor: tokens.colors.primary,\n"
            "  },\n"
            "  secondary: {\n"
            "    backgroundColor: tokens.colors.surfaceSubtle,\n"
            "  },\n"
            "  outline: {\n"
            "    backgroundColor: 'transparent',\n"
            "    borderWidth: 1,\n"
            "    borderColor: tokens.colors.border,\n"
            "  },\n"
            "  ghost: {\n"
            "    backgroundColor: 'transparent',\n"
            "  },\n"
            "  danger: {\n"
            "    backgroundColor: tokens.colors.danger,\n"
            "  },\n"
            "  disabled: {\n"
            "    opacity: 0.5,\n"
            "  },\n"
            "  text: {\n"
            "    fontWeight: '600',\n"
            "  },\n"
            "});\n\n"
            "const sizeStyles = StyleSheet.create({\n"
            "  sm: { paddingVertical: 6, paddingHorizontal: 12 },\n"
            "  md: { paddingVertical: 12, paddingHorizontal: 18 },\n"
            "  lg: { paddingVertical: 16, paddingHorizontal: 24 },\n"
            "});\n\n"
            "const textSizeStyles = StyleSheet.create({\n"
            "  sm: { fontSize: tokens.fontSize.xs },\n"
            "  md: { fontSize: tokens.fontSize.md },\n"
            "  lg: { fontSize: tokens.fontSize.lg },\n"
            "});\n\n"
            "const textVariants = StyleSheet.create({\n"
            "  primary: { color: '#ffffff' },\n"
            "  secondary: { color: tokens.colors.text },\n"
            "  outline: { color: tokens.colors.text },\n"
            "  ghost: { color: tokens.colors.primary },\n"
            "  danger: { color: '#ffffff' },\n"
            "});\n"
        )
        return GeneratedFile("src/design-system/components/Button.tsx", content)

    def _generate_card_component(self) -> GeneratedFile:
        content = (
            "import React from 'react';\n"
            "import { View, StyleSheet, ViewProps } from 'react-native';\n"
            "import { tokens } from '../tokens';\n\n"
            "export interface CardProps extends ViewProps {\n"
            "  variant?: 'default' | 'elevated' | 'bordered';\n"
            "}\n\n"
            "export const Card: React.FC<CardProps> = ({\n"
            "  variant = 'default',\n"
            "  style,\n"
            "  children,\n"
            "  ...rest\n"
            "}) => {\n"
            "  return (\n"
            "    <View style={[styles.base, styles[variant], style]} {...rest}>\n"
            "      {children}\n"
            "    </View>\n"
            "  );\n"
            "};\n\n"
            "const styles = StyleSheet.create({\n"
            "  base: {\n"
            "    backgroundColor: tokens.colors.card,\n"
            "    borderRadius: tokens.radii.lg,\n"
            "    padding: tokens.spacing.md,\n"
            "    borderWidth: 1,\n"
            "    borderColor: tokens.colors.border,\n"
            "  },\n"
            "  default: {},\n"
            "  elevated: {\n"
            "    shadowColor: '#000',\n"
            "    shadowOffset: { width: 0, height: 4 },\n"
            "    shadowOpacity: 0.3,\n"
            "    shadowRadius: 8,\n"
            "    elevation: 4,\n"
            "  },\n"
            "  bordered: {\n"
            "    borderColor: tokens.colors.borderLight,\n"
            "  },\n"
            "});\n"
        )
        return GeneratedFile("src/design-system/components/Card.tsx", content)

    def _generate_badge_component(self) -> GeneratedFile:
        content = (
            "import React from 'react';\n"
            "import { View, Text, StyleSheet } from 'react-native';\n"
            "import { tokens } from '../tokens';\n\n"
            "export interface BadgeProps {\n"
            "  label: string;\n"
            "  variant?: 'primary' | 'success' | 'warning' | 'danger' | 'neutral';\n"
            "}\n\n"
            "export const Badge: React.FC<BadgeProps> = ({ label, variant = 'neutral' }) => {\n"
            "  return (\n"
            "    <View style={[styles.container, styles[variant]]}>\n"
            "      <Text style={[styles.label, labelVariants[variant]]}>{label}</Text>\n"
            "    </View>\n"
            "  );\n"
            "};\n\n"
            "const styles = StyleSheet.create({\n"
            "  container: {\n"
            "    paddingHorizontal: 8,\n"
            "    paddingVertical: 3,\n"
            "    borderRadius: tokens.radii.full,\n"
            "    alignSelf: 'flex-start',\n"
            "  },\n"
            "  primary: { backgroundColor: tokens.colors.primaryMuted },\n"
            "  success: { backgroundColor: tokens.colors.successBg },\n"
            "  warning: { backgroundColor: tokens.colors.warningBg },\n"
            "  danger: { backgroundColor: tokens.colors.dangerBg },\n"
            "  neutral: { backgroundColor: tokens.colors.surfaceSubtle },\n"
            "  label: {\n"
            "    fontSize: tokens.fontSize.xs,\n"
            "    fontWeight: '600',\n"
            "  },\n"
            "});\n\n"
            "const labelVariants = StyleSheet.create({\n"
            "  primary: { color: tokens.colors.primary },\n"
            "  success: { color: tokens.colors.success },\n"
            "  warning: { color: tokens.colors.warning },\n"
            "  danger: { color: tokens.colors.danger },\n"
            "  neutral: { color: tokens.colors.textMuted },\n"
            "});\n"
        )
        return GeneratedFile("src/design-system/components/Badge.tsx", content)

    def _generate_input_component(self) -> GeneratedFile:
        content = (
            "import React from 'react';\n"
            "import {\n"
            "  View,\n"
            "  Text,\n"
            "  TextInput,\n"
            "  StyleSheet,\n"
            "  TextInputProps,\n"
            "} from 'react-native';\n"
            "import { tokens } from '../tokens';\n\n"
            "export interface InputProps extends TextInputProps {\n"
            "  label?: string;\n"
            "  error?: string;\n"
            "}\n\n"
            "export const Input: React.FC<InputProps> = ({\n"
            "  label,\n"
            "  error,\n"
            "  style,\n"
            "  ...rest\n"
            "}) => {\n"
            "  return (\n"
            "    <View style={styles.container}>\n"
            "      {label && <Text style={styles.label}>{label}</Text>}\n"
            "      <TextInput\n"
            "        style={[styles.input, !!error && styles.inputError, style]}\n"
            "        placeholderTextColor={tokens.colors.textMuted}\n"
            "        {...rest}\n"
            "      />\n"
            "      {error && <Text style={styles.errorText}>{error}</Text>}\n"
            "    </View>\n"
            "  );\n"
            "};\n\n"
            "const styles = StyleSheet.create({\n"
            "  container: {\n"
            "    marginBottom: tokens.spacing.md,\n"
            "  },\n"
            "  label: {\n"
            "    fontSize: tokens.fontSize.sm,\n"
            "    color: tokens.colors.textMuted,\n"
            "    marginBottom: tokens.spacing.xs,\n"
            "    fontWeight: '500',\n"
            "  },\n"
            "  input: {\n"
            "    backgroundColor: tokens.colors.surface,\n"
            "    borderWidth: 1,\n"
            "    borderColor: tokens.colors.border,\n"
            "    borderRadius: tokens.radii.md,\n"
            "    paddingHorizontal: tokens.spacing.md,\n"
            "    paddingVertical: 12,\n"
            "    fontSize: tokens.fontSize.md,\n"
            "    color: tokens.colors.text,\n"
            "  },\n"
            "  inputError: {\n"
            "    borderColor: tokens.colors.danger,\n"
            "  },\n"
            "  errorText: {\n"
            "    color: tokens.colors.danger,\n"
            "    fontSize: tokens.fontSize.xs,\n"
            "    marginTop: 4,\n"
            "  },\n"
            "});\n"
        )
        return GeneratedFile("src/design-system/components/Input.tsx", content)

    def _generate_stat_card_component(self) -> GeneratedFile:
        content = (
            "import React from 'react';\n"
            "import { View, Text, StyleSheet } from 'react-native';\n"
            "import { Card } from './Card';\n"
            "import { Badge } from './Badge';\n"
            "import { tokens } from '../tokens';\n\n"
            "export interface StatCardProps {\n"
            "  title: string;\n"
            "  value: string | number;\n"
            "  subtext?: string;\n"
            "  variant?: 'primary' | 'success' | 'neutral';\n"
            "}\n\n"
            "export const StatCard: React.FC<StatCardProps> = ({\n"
            "  title,\n"
            "  value,\n"
            "  subtext,\n"
            "  variant = 'neutral',\n"
            "}) => {\n"
            "  return (\n"
            "    <Card style={styles.card}>\n"
            "      <Text style={styles.title}>{title}</Text>\n"
            "      <Text style={styles.value}>{value}</Text>\n"
            "      {subtext && (\n"
            "        <View style={styles.subtextContainer}>\n"
            "          <Badge label={subtext} variant={variant} />\n"
            "        </View>\n"
            "      )}\n"
            "    </Card>\n"
            "  );\n"
            "};\n\n"
            "const styles = StyleSheet.create({\n"
            "  card: {\n"
            "    flex: 1,\n"
            "    minWidth: 140,\n"
            "    margin: 4,\n"
            "  },\n"
            "  title: {\n"
            "    fontSize: tokens.fontSize.xs,\n"
            "    color: tokens.colors.textMuted,\n"
            "    textTransform: 'uppercase',\n"
            "    fontWeight: '600',\n"
            "    letterSpacing: 0.5,\n"
            "  },\n"
            "  value: {\n"
            "    fontSize: tokens.fontSize.xxl,\n"
            "    color: tokens.colors.text,\n"
            "    fontWeight: '700',\n"
            "    marginVertical: 4,\n"
            "  },\n"
            "  subtextContainer: {\n"
            "    marginTop: 2,\n"
            "  },\n"
            "});\n"
        )
        return GeneratedFile("src/design-system/components/StatCard.tsx", content)

    def _generate_screen_container(self) -> GeneratedFile:
        content = (
            "import React from 'react';\n"
            "import {\n"
            "  View,\n"
            "  StyleSheet,\n"
            "  ScrollView,\n"
            "  KeyboardAvoidingView,\n"
            "  Platform,\n"
            "} from 'react-native';\n"
            "import { SafeAreaView } from 'react-native-safe-area-context';\n"
            "import { tokens } from '../tokens';\n\n"
            "export interface ScreenContainerProps {\n"
            "  children: React.ReactNode;\n"
            "  scrollable?: boolean;\n"
            "}\n\n"
            "export const ScreenContainer: React.FC<ScreenContainerProps> = ({\n"
            "  children,\n"
            "  scrollable = true,\n"
            "}) => {\n"
            "  return (\n"
            "    <SafeAreaView style={styles.safeArea}>\n"
            "      <KeyboardAvoidingView\n"
            "        style={styles.keyboardAvoid}\n"
            "        behavior={Platform.OS === 'ios' ? 'padding' : undefined}\n"
            "      >\n"
            "        {scrollable ? (\n"
            "          <ScrollView\n"
            "            contentContainerStyle={styles.scrollContent}\n"
            "            showsVerticalScrollIndicator={false}\n"
            "          >\n"
            "            {children}\n"
            "          </ScrollView>\n"
            "        ) : (\n"
            "          <View style={styles.staticContent}>{children}</View>\n"
            "        )}\n"
            "      </KeyboardAvoidingView>\n"
            "    </SafeAreaView>\n"
            "  );\n"
            "};\n\n"
            "const styles = StyleSheet.create({\n"
            "  safeArea: {\n"
            "    flex: 1,\n"
            "    backgroundColor: tokens.colors.background,\n"
            "  },\n"
            "  keyboardAvoid: {\n"
            "    flex: 1,\n"
            "  },\n"
            "  scrollContent: {\n"
            "    padding: tokens.spacing.md,\n"
            "    paddingBottom: 40,\n"
            "  },\n"
            "  staticContent: {\n"
            "    flex: 1,\n"
            "    padding: tokens.spacing.md,\n"
            "  },\n"
            "});\n"
        )
        return GeneratedFile("src/design-system/components/ScreenContainer.tsx", content)

    # ── Shared API & Auth ──────────────────────────────────────────────────────

    def _generate_api_client(self) -> GeneratedFile:
        content = (
            "// Typed HTTP Client for OmniStackAI Backend API\n"
            "const BASE_URL = process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000';\n\n"
            "let authToken: string | null = null;\n\n"
            "export const setAuthToken = (token: string | null) => {\n"
            "  authToken = token;\n"
            "};\n\n"
            "async function request<T>(path: string, options: RequestInit = {}): Promise<T> {\n"
            "  const headers: Record<string, string> = {\n"
            "    'Content-Type': 'application/json',\n"
            "    ...(options.headers as Record<string, string>),\n"
            "  };\n"
            "  if (authToken) {\n"
            "    headers['Authorization'] = `Bearer ${authToken}`;\n"
            "  }\n"
            "  const url = `${BASE_URL.replace(/\\/$/, '')}/${path.replace(/^\\//, '')}`;\n"
            "  const res = await fetch(url, { ...options, headers });\n"
            "  if (!res.ok) {\n"
            "    const errorBody = await res.json().catch(() => ({}));\n"
            "    throw new Error(errorBody.detail || errorBody.message || `Request failed with status ${res.status}`);\n"
            "  }\n"
            "  return res.json();\n"
            "}\n\n"
            "export const apiClient = {\n"
            "  get: <T>(path: string) => request<T>(path, { method: 'GET' }),\n"
            "  post: <T>(path: string, body: unknown) => request<T>(path, { method: 'POST', body: JSON.stringify(body) }),\n"
            "  put: <T>(path: string, body: unknown) => request<T>(path, { method: 'PUT', body: JSON.stringify(body) }),\n"
            "  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),\n"
            "};\n"
        )
        return GeneratedFile("src/shared/api/client.ts", content)

    def _generate_auth_context(self, ir: ApplicationIR) -> GeneratedFile:  # noqa: ARG002
        # R-591: a real session — sign-in, sign-up, recovery, and a token kept in secure storage.
        # The previous context only held a token somebody else had to supply; no screen did.
        content = RN_AUTH_CONTEXT
        return GeneratedFile("src/shared/auth/AuthContext.tsx", content)

    # ── Per-Entity Features ────────────────────────────────────────────────────

    def _generate_entity_feature(self, entity: Entity, ir: ApplicationIR) -> list[GeneratedFile]:
        slug = _to_snake(entity.name)
        pascal = _to_pascal(entity.name)
        primary_field = entity.fields[0].name if entity.fields else "id"
        files: list[GeneratedFile] = []

        # 1. Model Types
        field_lines = ["  id: string;"]
        for f in entity.fields:
            if f.name.lower() == "id":
                continue
            ts_type = _ts_field_type(f.type)
            opt = "" if f.required else "?"
            field_lines.append(f"  {f.name}{opt}: {ts_type};")

        type_content = (
            f"export interface {pascal} {{\n"
            + "\n".join(field_lines)
            + "\n}\n\n"
            f"export type Create{pascal}Input = Omit<{pascal}, 'id'>;\n"
            f"export type Update{pascal}Input = Partial<Create{pascal}Input>;\n"
        )
        files.append(GeneratedFile(f"src/features/{slug}/model/types.ts", type_content))

        # 2. API Client
        api_template = """import { apiClient } from '../../../shared/api/client';
import { __PASCAL__, Create__PASCAL__Input, Update__PASCAL__Input } from '../model/types';

const ENDPOINT = '/api/__SLUG__s';

export const __SLUG__Api = {
  list: () => apiClient.get<__PASCAL__[]>(ENDPOINT),
  get: (id: string) => apiClient.get<__PASCAL__>(`${ENDPOINT}/${id}`),
  create: (data: Create__PASCAL__Input) => apiClient.post<__PASCAL__>(ENDPOINT, data),
  update: (id: string, data: Update__PASCAL__Input) => apiClient.put<__PASCAL__>(`${ENDPOINT}/${id}`, data),
  delete: (id: string) => apiClient.delete<{ success: boolean }>(`${ENDPOINT}/${id}`),
};
"""
        api_content = (
            api_template
            .replace("__PASCAL__", pascal)
            .replace("__SLUG__", slug)
        )
        files.append(GeneratedFile(f"src/features/{slug}/api/client.ts", api_content))

        # 3. Hooks
        hook_template = """import { useState, useEffect, useCallback } from 'react';
import { __PASCAL__, Create__PASCAL__Input, Update__PASCAL__Input } from '../model/types';
import { __SLUG__Api } from '../api/client';

export const use__PASCAL__s = () => {
  const [items, setItems] = useState<__PASCAL__[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchItems = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await __SLUG__Api.list();
      setItems(data ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchItems();
  }, [fetchItems]);

  const createItem = async (input: Create__PASCAL__Input) => {
    const created = await __SLUG__Api.create(input);
    setItems((prev) => [...prev, created]);
    return created;
  };

  const updateItem = async (id: string, input: Update__PASCAL__Input) => {
    const updated = await __SLUG__Api.update(id, input);
    setItems((prev) => prev.map((item) => (item.id === id ? updated : item)));
    return updated;
  };

  const deleteItem = async (id: string) => {
    await __SLUG__Api.delete(id);
    setItems((prev) => prev.filter((item) => item.id !== id));
  };

  return {
    items,
    loading,
    error,
    refresh: fetchItems,
    createItem,
    updateItem,
    deleteItem,
  };
};
"""
        hook_content = (
            hook_template
            .replace("__PASCAL__", pascal)
            .replace("__SLUG__", slug)
        )
        files.append(GeneratedFile(f"src/features/{slug}/hooks/use{pascal}.ts", hook_content))

        # 4. List Screen
        list_screen_template = """import React, { useState } from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  RefreshControl,
} from 'react-native';
import { ScreenContainer } from '../../../design-system/components/ScreenContainer';
import { Card } from '../../../design-system/components/Card';
import { Button } from '../../../design-system/components/Button';
import { StatCard } from '../../../design-system/components/StatCard';
import { Badge } from '../../../design-system/components/Badge';
import { tokens } from '../../../design-system/tokens';
import { use__PASCAL__s } from '../hooks/use__PASCAL__';
import { __PASCAL__ } from '../model/types';

export const __PASCAL__ListScreen = ({ navigation }: any) => {
  const { items, loading, error, refresh, deleteItem } = use__PASCAL__s();

  const renderItem = ({ item }: { item: __PASCAL__ }) => (
    <Card style={styles.itemCard}>
      <TouchableOpacity
        onPress={() => navigation.navigate('__PASCAL__Detail', { id: item.id, initial: item })}
      >
        <Text style={styles.itemTitle}>{String((item as any).__PRIMARY_FIELD__ || item.id)}</Text>
        <Text style={styles.itemId}>ID: {item.id}</Text>
      </TouchableOpacity>
      <View style={styles.itemActions}>
        <Button
          title="Delete"
          variant="danger"
          size="sm"
          onPress={() => void deleteItem(item.id)}
        />
      </View>
    </Card>
  );

  return (
    <ScreenContainer scrollable={false}>
      <View style={styles.header}>
        <Text style={styles.screenTitle}>__ENTITY_NAME__ Management</Text>
        <Button
          title="+ New"
          size="sm"
          onPress={() => navigation.navigate('__PASCAL__Detail', {})}
        />
      </View>

      <View style={styles.statsRow}>
        <StatCard title="Total __ENTITY_NAME__s" value={items.length} variant="primary" />
        <StatCard title="Sync Status" value="Active" subtext="Live" variant="success" />
      </View>

      {error && (
        <View style={styles.errorBox}>
          <Text style={styles.errorText}>{error}</Text>
        </View>
      )}

      <FlatList
        data={items}
        keyExtractor={(item) => item.id}
        renderItem={renderItem}
        contentContainerStyle={styles.listContent}
        refreshControl={
          <RefreshControl
            refreshing={loading}
            onRefresh={refresh}
            tintColor={tokens.colors.primary}
          />
        }
        ListEmptyComponent={
          !loading ? (
            <View style={styles.emptyState}>
              <Text style={styles.emptyText}>No __ENTITY_NAME__ records found.</Text>
            </View>
          ) : null
        }
      />
    </ScreenContainer>
  );
};

const styles = StyleSheet.create({
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: tokens.spacing.md,
  },
  screenTitle: {
    fontSize: tokens.fontSize.xl,
    fontWeight: '700',
    color: tokens.colors.text,
  },
  statsRow: {
    flexDirection: 'row',
    marginBottom: tokens.spacing.md,
  },
  listContent: {
    paddingBottom: 40,
  },
  itemCard: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: tokens.spacing.sm,
  },
  itemTitle: {
    fontSize: tokens.fontSize.md,
    fontWeight: '600',
    color: tokens.colors.text,
  },
  itemId: {
    fontSize: tokens.fontSize.xs,
    color: tokens.colors.textMuted,
    marginTop: 2,
  },
  itemActions: {
    marginLeft: tokens.spacing.sm,
  },
  emptyState: {
    padding: 32,
    alignItems: 'center',
  },
  emptyText: {
    color: tokens.colors.textMuted,
    fontSize: tokens.fontSize.sm,
  },
  errorBox: {
    backgroundColor: tokens.colors.dangerBg,
    padding: 10,
    borderRadius: tokens.radii.md,
    marginBottom: 10,
  },
  errorText: {
    color: tokens.colors.danger,
    fontSize: tokens.fontSize.xs,
  },
});
"""
        list_screen_content = (
            list_screen_template
            .replace("__PASCAL__", pascal)
            .replace("__SLUG__", slug)
            .replace("__ENTITY_NAME__", entity.name)
            .replace("__PRIMARY_FIELD__", primary_field)
        )
        files.append(GeneratedFile(f"src/features/{slug}/ui/{pascal}ListScreen.tsx", list_screen_content))

        # 5. Detail / Editor Screen
        form_inputs: list[str] = []
        state_inits: list[str] = []
        payload_assignments: list[str] = []
        for f in entity.fields:
            if f.name.lower() == "id":
                continue
            state_inits.append(f"  const [{f.name}, set{_to_pascal(f.name)}] = useState(initial?.{f.name} ? String(initial.{f.name}) : '');")
            form_inputs.append(
                f'        <Input\n'
                f'          label="{f.name.capitalize()}"\n'
                f'          value={{{f.name}}}\n'
                f'          onChangeText={{set{_to_pascal(f.name)}}}\n'
                f'          placeholder="Enter {f.name}"\n'
                f'        />'
            )
            if f.type in (FieldType.INT, FieldType.FLOAT):
                payload_assignments.append(f"      payload.{f.name} = Number({f.name}) || 0;")
            elif f.type is FieldType.BOOL:
                payload_assignments.append(f"      payload.{f.name} = {f.name}.toLowerCase() === 'true';")
            else:
                payload_assignments.append(f"      payload.{f.name} = {f.name};")

        detail_screen_template = """import React, { useState } from 'react';
import { View, Text, StyleSheet, Alert } from 'react-native';
import { ScreenContainer } from '../../../design-system/components/ScreenContainer';
import { Card } from '../../../design-system/components/Card';
import { Button } from '../../../design-system/components/Button';
import { Input } from '../../../design-system/components/Input';
import { tokens } from '../../../design-system/tokens';
import { __SLUG__Api } from '../api/client';

export const __PASCAL__DetailScreen = ({ route, navigation }: any) => {
  const { id, initial } = route.params || {};
  const isEditing = Boolean(id);
  const [loading, setLoading] = useState(false);
__STATE_INITS__

  const handleSave = async () => {
    setLoading(true);
    try {
      const payload: any = {};
__PAYLOAD_ASSIGNMENTS__
      if (isEditing) {
        await __SLUG__Api.update(id, payload);
      } else {
        await __SLUG__Api.create(payload);
      }
      navigation.goBack();
    } catch (err) {
      Alert.alert('Save Failed', err instanceof Error ? err.message : 'Error saving record');
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScreenContainer scrollable={true}>
      <Text style={styles.title}>{isEditing ? 'Edit' : 'Create'} __ENTITY_NAME__</Text>
      <Card style={styles.formCard}>
__FORM_INPUTS__
        <Button
          title={isEditing ? 'Save Changes' : 'Create Record'}
          onPress={handleSave}
          loading={loading}
          style={styles.saveButton}
        />
      </Card>
    </ScreenContainer>
  );
};

const styles = StyleSheet.create({
  title: {
    fontSize: tokens.fontSize.xl,
    fontWeight: '700',
    color: tokens.colors.text,
    marginBottom: tokens.spacing.md,
  },
  formCard: {
    padding: tokens.spacing.lg,
  },
  saveButton: {
    marginTop: tokens.spacing.md,
  },
});
"""
        detail_screen_content = (
            detail_screen_template
            .replace("__PASCAL__", pascal)
            .replace("__SLUG__", slug)
            .replace("__ENTITY_NAME__", entity.name)
            .replace("__STATE_INITS__", "\n".join(state_inits))
            .replace("__PAYLOAD_ASSIGNMENTS__", "\n".join(payload_assignments))
            .replace("__FORM_INPUTS__", "\n".join(form_inputs))
        )
        files.append(GeneratedFile(f"src/features/{slug}/ui/{pascal}DetailScreen.tsx", detail_screen_content))

        return files

    # ── App Overview & Navigation ──────────────────────────────────────────────

    def _generate_overview_screen(self, ir: ApplicationIR) -> GeneratedFile:
        entity_nav_cards: list[str] = []
        for entity in ir.entities:
            pascal = _to_pascal(entity.name)
            card_str = (
                "        <Card style={styles.entityCard}>\n"
                "          <View style={styles.entityInfo}>\n"
                f"            <Text style={{styles.entityName}}>{entity.name}</Text>\n"
                f"            <Text style={{styles.entityDesc}}>{len(entity.fields)} fields • Full CRUD</Text>\n"
                "          </View>\n"
                "          <Button\n"
                '            title="Open"\n'
                '            size="sm"\n'
                f"            onPress={{() => navigation.navigate('{pascal}List')}}\n"
                "          />\n"
                "        </Card>"
            )
            entity_nav_cards.append(card_str)

        # R-545: this file is emitted at src/app/screens/OverviewScreen.tsx, so reaching
        # src/design-system takes two levels (screens -> app -> src). It used one, and Metro
        # failed to resolve every component on the app's own home screen — the first thing a
        # phone would have tried to render. The navigator and App.tsx depths were already right.
        overview_template = """import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { ScreenContainer } from '../../design-system/components/ScreenContainer';
import { Card } from '../../design-system/components/Card';
import { StatCard } from '../../design-system/components/StatCard';
import { Badge } from '../../design-system/components/Badge';
import { Button } from '../../design-system/components/Button';
import { tokens } from '../../design-system/tokens';

export const OverviewScreen = ({ navigation }: any) => {
  return (
    <ScreenContainer scrollable={true}>
      {/* Hero Welcome */}
      <Card style={styles.heroCard}>
        <Badge label="OmniStackAI Mobile" variant="primary" />
        <Text style={styles.heroTitle}>__APP_NAME__</Text>
        <Text style={styles.heroSubtext}>
          __APP_DESC__
        </Text>
      </Card>

      {/* KPI Metrics */}
      <Text style={styles.sectionHeader}>System Metrics</Text>
      <View style={styles.statsRow}>
        <StatCard title="Entities" value="__ENTITY_COUNT__" variant="primary" />
        <StatCard title="Screens" value="__SCREEN_COUNT__" variant="success" />
      </View>

      {/* Feature Modules */}
      <Text style={styles.sectionHeader}>App Modules</Text>
__ENTITY_NAV_CARDS__
    </ScreenContainer>
  );
};

const styles = StyleSheet.create({
  heroCard: {
    marginBottom: tokens.spacing.lg,
    padding: tokens.spacing.lg,
  },
  heroTitle: {
    fontSize: tokens.fontSize.xxl,
    fontWeight: '800',
    color: tokens.colors.text,
    marginTop: tokens.spacing.sm,
  },
  heroSubtext: {
    fontSize: tokens.fontSize.sm,
    color: tokens.colors.textMuted,
    marginTop: 4,
    lineHeight: 20,
  },
  sectionHeader: {
    fontSize: tokens.fontSize.md,
    fontWeight: '700',
    color: tokens.colors.text,
    marginBottom: tokens.spacing.sm,
    marginTop: tokens.spacing.xs,
  },
  statsRow: {
    flexDirection: 'row',
    marginBottom: tokens.spacing.md,
  },
  entityCard: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: tokens.spacing.sm,
  },
  entityInfo: {
    flex: 1,
  },
  entityName: {
    fontSize: tokens.fontSize.md,
    fontWeight: '600',
    color: tokens.colors.text,
  },
  entityDesc: {
    fontSize: tokens.fontSize.xs,
    color: tokens.colors.textMuted,
    marginTop: 2,
  },
});
"""
        content = (
            overview_template
            .replace("__APP_NAME__", ir.name)
            .replace("__APP_DESC__", ir.description)
            .replace("__ENTITY_COUNT__", str(len(ir.entities)))
            .replace("__SCREEN_COUNT__", str(len(ir.screens)))
            .replace("__ENTITY_NAV_CARDS__", "\n".join(entity_nav_cards))
        )
        return GeneratedFile("src/app/screens/OverviewScreen.tsx", content)

    def _generate_root_navigator(self, ir: ApplicationIR) -> GeneratedFile:
        imports: list[str] = [
            "import React from 'react';",
            "import { createNativeStackNavigator } from '@react-navigation/native-stack';",
            "import { OverviewScreen } from '../screens/OverviewScreen';",
            *(["import { AuthHeaderButton, ForgotPasswordScreen, LoginScreen, RegisterScreen } from '../screens/AuthScreens';"]
              if needs_auth(ir) else []),
            "import { tokens } from '../../design-system/tokens';",
        ]
        if needs_auth(ir):
            # R-591: sign in / sign out from the home header, and the three account screens.
            screens: list[str] = [
                '      <Stack.Screen name="Overview" component={OverviewScreen} options={({ navigation }) => ({ title: "'
                + ir.name
                + '", headerRight: () => <AuthHeaderButton navigation={navigation} /> })} />',
                '      <Stack.Screen name="Login" component={LoginScreen} options={{ title: "Sign in" }} />',
                '      <Stack.Screen name="Register" component={RegisterScreen} options={{ title: "Create account" }} />',
                '      <Stack.Screen name="ForgotPassword" component={ForgotPasswordScreen} options={{ title: "Reset password" }} />',
            ]
        else:
            screens = [
                '      <Stack.Screen name="Overview" component={OverviewScreen} options={{ title: "'
                + ir.name
                + '" }} />'
            ]

        for entity in ir.entities:
            slug = _to_snake(entity.name)
            pascal = _to_pascal(entity.name)
            imports.append(f"import {{ {pascal}ListScreen }} from '../../features/{slug}/ui/{pascal}ListScreen';")
            imports.append(f"import {{ {pascal}DetailScreen }} from '../../features/{slug}/ui/{pascal}DetailScreen';")
            screens.append(f'      <Stack.Screen name="{pascal}List" component={{{pascal}ListScreen}} options={{{{ title: "{entity.name}s" }}}} />')
            screens.append(f'      <Stack.Screen name="{pascal}Detail" component={{{pascal}DetailScreen}} options={{{{ title: "{entity.name} Details" }}}} />')

        content = (
            "\n".join(imports)
            + "\n\n"
            "const Stack = createNativeStackNavigator();\n\n"
            "export const RootNavigator: React.FC = () => {\n"
            "  return (\n"
            "    <Stack.Navigator\n"
            '      initialRouteName="Overview"\n'
            "      screenOptions={{\n"
            "        headerStyle: { backgroundColor: tokens.colors.surface },\n"
            "        headerTintColor: tokens.colors.text,\n"
            "        headerTitleStyle: { fontWeight: '700' },\n"
            "        contentStyle: { backgroundColor: tokens.colors.background },\n"
            "      }}\n"
            "    >\n"
            + "\n".join(screens)
            + "\n"
            "    </Stack.Navigator>\n"
            "  );\n"
            "};\n"
        )
        return GeneratedFile("src/app/navigation/RootNavigator.tsx", content)

    def _generate_app_root(self, ir: ApplicationIR) -> GeneratedFile:
        content = (
            "import React from 'react';\n"
            "import { StatusBar } from 'expo-status-bar';\n"
            "import { SafeAreaProvider } from 'react-native-safe-area-context';\n"
            "import { NavigationContainer } from '@react-navigation/native';\n"
            "import { AuthProvider } from '../shared/auth/AuthContext';\n"
            "import { RootNavigator } from './navigation/RootNavigator';\n\n"
            "export default function App() {\n"
            "  return (\n"
            "    <SafeAreaProvider>\n"
            "      <AuthProvider>\n"
            "        <NavigationContainer>\n"
            '          <StatusBar style="light" />\n'
            "          <RootNavigator />\n"
            "        </NavigationContainer>\n"
            "      </AuthProvider>\n"
            "    </SafeAreaProvider>\n"
            "  );\n"
            "}\n"
        )
        return GeneratedFile("src/app/App.tsx", content)
