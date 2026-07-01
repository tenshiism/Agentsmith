# VRM Avatar Models

AgentSmith uses VRM avatar models for the VTuber overlay. These models are **not** included in the git repo by default. Download them and place them in `assets/models/`.

## Required Models

| Model | File | Download | License |
|-------|------|----------|---------|
| Seed-san | `Seed-san.vrm` | [GitHub](https://github.com/vrm-c/vrm-specification/raw/master/samples/Seed-san/vrm/Seed-san.vrm) | VRM Public License 1.0 |
| Alicia Solid | `AliciaSolid_vrm-0.51.vrm` | [GitHub](https://github.com/vrm-c/UniVRM/raw/master/Tests/Models/Alicia_vrm-0.51/AliciaSolid_vrm-0.51.vrm) | VRM Public License 1.0 |
| ExampleAvatar A | `ExampleAvatar_A.vrm` | [GitHub](https://github.com/scorpionknifes/VRM-examples/raw/main/ExampleAvatar_A.vrm) | VRoid Sample Terms |
| ExampleAvatar C | `ExampleAvatar_C.vrm` | [GitHub](https://github.com/scorpionknifes/VRM-examples/raw/main/ExampleAvatar_C.vrm) | VRoid Sample Terms |
| Avatar Orion | `Avatar_Orion.vrm` | Included in repo | Unknown — contact maintainer |

## Quick Download (PowerShell)

```powershell
Invoke-WebRequest -Uri "https://github.com/vrm-c/vrm-specification/raw/master/samples/Seed-san/vrm/Seed-san.vrm" -OutFile "assets/models/Seed-san.vrm"
Invoke-WebRequest -Uri "https://github.com/vrm-c/UniVRM/raw/master/Tests/Models/Alicia_vrm-0.51/AliciaSolid_vrm-0.51.vrm" -OutFile "assets/models/AliciaSolid_vrm-0.51.vrm"
Invoke-WebRequest -Uri "https://github.com/scorpionknifes/VRM-examples/raw/main/ExampleAvatar_A.vrm" -OutFile "assets/models/ExampleAvatar_A.vrm"
Invoke-WebRequest -Uri "https://github.com/scorpionknifes/VRM-examples/raw/main/ExampleAvatar_C.vrm" -OutFile "assets/models/ExampleAvatar_C.vrm"
```

## Adding More Models

1. Export or download any `.vrm` file
2. Place it in `assets/models/`
3. Add an entry to the `MODELS` array in `assets/js/overlay.js`:
   ```js
   const MODELS = [
     { name: 'Seed-san',          file: '/assets/models/Seed-san.vrm' },
     { name: 'Alicia Solid',      file: '/assets/models/AliciaSolid_vrm-0.51.vrm' },
     { name: 'Your New Model',    file: '/assets/models/your-model.vrm' },
   ];
   ```
4. The dropdown in the settings modal updates automatically
