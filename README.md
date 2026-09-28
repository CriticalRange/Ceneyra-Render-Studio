# Ceneyra Render Studio

Ceneyra Render Studio is a 3ds Max MAXScript panel for safely preparing product material variants, UVW mapping, previews, and queued catalogue renders.

## Supported environment

- Windows
- Autodesk 3ds Max 2024
- Chaos V-Ray 7 Update 2 Hotfix 2 (CPU) for V-Ray preview and render operations

Other 3ds Max or V-Ray versions have not been qualified for this build.

## Install and start

1. Extract the complete package into a stable folder. Keep all `CRS_*.ms` files beside `Ceneyra_Render_Studio.ms`.
2. Start `Launch-Ceneyra-Render-Studio.bat`, or open a scene in 3ds Max and run `Ceneyra_Render_Studio.ms` from **Scripting > Run Script**.
3. To use the launcher with a scene, paste its full path when prompted. The scene is opened in 3ds Max; the Studio scripts do not save over it.
4. In the panel, create a safe working copy before changing materials or UVW. Confirm the object bindings and camera selection before rendering.

The launcher expects the default 3ds Max 2024 installation under `%ProgramFiles%\Autodesk\3ds Max 2024`. If Max is installed elsewhere, launch the script from inside Max.

## Render behavior

- The default output dimensions are 2000 × 3000 pixels and can be changed in the panel.
- V-Ray draft and queued renders run in a separate 3ds Max process.
- Output queues and working scene copies are written under the Studio folder. Keep that folder writable and on a drive with enough free space.
- A Render Mask PATCH is a partial pass, not a replacement for a complete beauty render.
- Product scenes, textures, 3ds Max, and V-Ray are not included in this package.

The KA1546 one-click mapping depends on the scene's expected object and material structure. Use manual binding for other scene structures and inspect all mappings before rendering.

## Source tests

The MAXScript test suite is kept in the source project, not in the runtime package. Tests that load a scene require a disposable scene copy supplied through the `CRS_TEST_SCENE` environment variable. Never point tests at a production original.

Example PowerShell setup before running one of the test scripts:

```powershell
$env:CRS_TEST_SCENE = 'D:\Scenes\KA1546-test-copy.max'
& "$env:ProgramFiles\Autodesk\3ds Max 2024\3dsmaxbatch.exe" '.\CRS_Tests.ms' -safescene on -v 2
```

Older render, worker, and GUI result files record passing runs. The core result currently present in the folder reports a missing texture from an outdated local fixture, so it is not a clean release signal. The new fixture-path configuration has not yet been rerun; run the full suite with the intended fixture on the release machine before tagging a GitHub release.

## Repository contents

The source repository includes the MAXScript modules and test scripts. Scene files, generated renders, local caches, result logs, user-specific launchers, and the internal `AGENTS.md` are excluded from Git tracking. No open-source license is included; add a license only after choosing the intended reuse terms.