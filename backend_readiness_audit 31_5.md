# NEXUS-R Backend Readiness Audit

## 1. Backend Architecture Overview

*   **Backend folder structure**: The Python backend is heavily modularized under `modules/` including: `cli`, `cognition_router`, `execution_sandbox`, `input_gateway`, `orchestrator`, `session_manager`, `state_core`, `trust_layer`, `web_ui`, and `workflow_engine`. It runs as a spawned `child_process` from Electron (`modules.cli.src.main dashboard start`).
*   **Electron IPC structure**: Managed in `desktop-app/main.js` and exposed via `desktop-app/preload.js`. Uses simple JSON file storage (`settings.json`) located in `app.getPath('userData')`.
*   **Zustand store structure**: Located in `frontend/src/store/`. Currently contains only `useAppStore.ts` (Chat/State), `appearanceStore.ts` (Theme), and `performanceStore.ts` (Resource limits).
*   **API/service layer structure**: A REST and WebSocket API runs on port 8000 via FastAPI (`modules/web_ui/src/app.py`). The frontend client (`frontend/src/api/client.ts`) communicates using standard `fetch`.
*   **Database/storage structure**: Python backend utilizes an `event_store` and `etd_store` for persisting chat memory, costs, and traces. Electron utilizes a local `settings.json` file for system settings.

## 2. Feature Completion Matrix

| Feature | Backend Exists | IPC Exists | Store Exists | Ready For UI |
| ------- | -------------- | ---------- | ------------ | ------------ |
| Chat | Yes (`chat_handler.py`) | N/A (REST API) | Yes (`useAppStore.ts`) | **READY** |
| Models | Yes (`model_manager.py`) | No | No | **NOT READY** |
| Providers | Yes (`secret_registry.py`)| No | No | **NOT READY** |
| Memory | Yes (`app.py` REST API) | N/A (REST API) | No | **PARTIAL** |
| Appearance | Yes (`settings.json`) | Yes | Yes (`appearanceStore.ts`) | **PARTIAL** |
| Performance | Yes (`settings.json`) | Yes | Yes (`performanceStore.ts`)| **READY** |
| Authentication | No | No | No | **NOT READY** |
| Settings | Yes (Partially) | Yes (Partially)| Yes (Partially) | **PARTIAL** |
| Routing | Yes (`cognition_router`) | No | No | **NOT READY** |
| Agent System | Yes (`workflow_engine`) | No | No | **NOT READY** |
| Tools | Yes (`execution_sandbox`) | No | No | **NOT READY** |
| RAG | Yes | No | No | **NOT READY** |
| Local Models | Yes (`model_manager.py`) | No | No | **NOT READY** |
| Cloud Models | Yes (`model_manager.py`) | No | No | **NOT READY** |

## 3. IPC Audit

**`ipcMain.handle()` bindings (in `main.js`) & `ipcRenderer.invoke()` (in `preload.js`):**

*   `appearance:getSettings` - **Dead/Unused handler** (The UI's `appearanceStore.ts` uses `zustand/persist` and ignores IPC entirely).
*   `appearance:saveSettings` - **Dead/Unused handler**.
*   `appearance:getSystemTheme` - **Dead/Unused handler**.
*   `appearance:importTheme` - **Dead/Unused handler** (`appearanceStore.ts` uses native DOM `<input type="file">` instead).
*   `appearance:exportTheme` - **Dead/Unused handler** (`appearanceStore.ts` uses native DOM `Blob` instead).
*   `performance:getSettings` - **Connected handler** (Used directly by `performanceStore.ts`).
*   `performance:saveSettings` - **Connected handler** (Used directly by `performanceStore.ts`).

## 4. API Contract Audit

Based on `modules/web_ui/src/app.py`:

*   `/api/v1/chat` (POST)
    *   **Request schema**: `ChatRequest` (message: str, model?: str, conversation_id?: str, images?: list)
    *   **Response schema**: Streaming JSON skeleton or Processing status.
    *   **Status**: Connected via `useAppStore.ts`.
*   `/api/v1/chat/hitl-resume` (POST)
    *   **Request schema**: `HITLResumeRequest` (message_id: str, code?: str, solved: bool)
    *   **Status**: **Missing contract in UI** (`useAppStore.ts` does not implement this).
*   `/api/v1/memory` (GET, DELETE, POST)
    *   **Status**: **Missing contract in UI**. No `client.ts` or Zustand store fetches this data.
*   `/api/v1/cost/*` & `/api/v1/telemetry`
    *   **Status**: Backend exposes these for the Dev Monitor, partially integrated.

**Identify:**
*   **Missing contracts**: There are absolutely NO REST endpoints in `app.py` for fetching, creating, or updating **Providers** or **Models**.

## 5. Zustand Integration Audit

*   **`useAppStore.ts`**:
    *   Real backend data: Yes (REST `/api/v1/chat`).
    *   Missing actions: HITL Resume, Memory fetching.
*   **`appearanceStore.ts`**:
    *   Mock data: No.
    *   Real backend data: No. Uses strictly local browser storage (`zustand/persist`).
    *   Missing persistence: Fails to sync with the Electron backend's `settings.json`.
*   **`performanceStore.ts`**:
    *   Real backend data: Yes (IPC connected).
    *   Missing persistence: None. Fully functional.

## 6. UI Integration Readiness

*   **AppearancePage**: **PARTIAL**. The UI is beautiful and functional, but it bypasses the Electron IPC backend entirely in favor of browser-local `zustand/persist`. It will not sync across app restarts if local storage clears.
*   **GeneralPage**: **NOT READY**. Hardcoded React state. No Zustand store exists. No IPC or API endpoints exist for General settings.
*   **MemoryPage**: **NOT READY**. The UI is entirely hardcoded. The backend REST API (`/api/v1/memory`) exists, but there is no Zustand store to bridge them.
*   **ModelsPage**: **NOT READY**. Completely hardcoded React state. Python backend (`model_manager.py`) exists but lacks REST API endpoints in `app.py`.
*   **PerformancePage**: **READY**. Correctly utilizes `usePerformanceStore.ts` which is wired perfectly to IPC.
*   **ProvidersPage**: **NOT READY**. Completely hardcoded React UI (`providersList`). No Zustand store. Python backend (`secret_registry.py`) lacks REST API endpoints.

## 7. Missing Backend Work

| Priority | Component | Missing Work | Blocks UI? |
| :--- | :--- | :--- | :--- |
| **High** | Providers API | Create REST endpoints in `app.py` to interface with `secret_registry.py` (GET/POST/DELETE API keys). | Yes |
| **High** | Models API | Create REST endpoints in `app.py` to interface with `model_manager.py` (List active models, change default model). | Yes |
| **Medium** | Memory Store | Create `memoryStore.ts` in the frontend to connect the existing `/api/v1/memory` REST endpoints to `MemoryPage.tsx`. | Yes |
| **Medium** | Appearance IPC | Refactor `appearanceStore.ts` to actually utilize the existing `ipcRenderer.invoke('appearance:*')` bindings instead of local DOM storage. | No |
| **Low** | General Settings | Create `generalStore.ts` and corresponding IPC endpoints in `main.js`. | Yes |

## 8. Integration Risk Assessment

*   **Backend completeness**: ~80% (Core AI modules exist, but REST bridging is missing).
*   **IPC completeness**: ~20% (Many dead handlers, appearance bypassing).
*   **Store completeness**: ~30% (Only Chat, Appearance, and Performance stores exist).
*   **API completeness**: ~40% (Chat and Memory exist, but Settings/Providers/Models are completely missing).
*   **Overall UI integration readiness**: **~30%**

## 9. Final Verdict

**D. Backend requires major work before integration**

**Reasoning & Evidence:**
While the Python core logic for Models and Providers exists (`model_manager.py` and `secret_registry.py`), the REST API gateway (`app.py`) **does not expose any endpoints** for the UI to consume them. Before the `ModelsPage.tsx` or `ProvidersPage.tsx` can be integrated, the backend team must build the bridging REST endpoints in `app.py`. Furthermore, the frontend is missing the necessary Zustand stores (`modelsStore.ts`, `providersStore.ts`, `memoryStore.ts`) to manage this state. It is impossible to begin UI integration for these pages because the API contracts literally do not exist.
