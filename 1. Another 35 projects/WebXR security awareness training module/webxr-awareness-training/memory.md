# WebXR Awareness - Memory Reference

## Key Concepts to Remember

### What is WebXR?
- WebXR is a web standard for VR/AR experiences in browsers
- Replaces the older WebVR standard
- Supported in Chrome, Edge, and some mobile browsers
- Uses the `navigator.xr` API

### Core WebXR Concepts

#### 1. XR Session
- The connection between your app and XR hardware
- Types: `immersive-vr`, `immersive-ar`, `inline`
- Managed through `XRSession` object

#### 2. XR Reference Space
- Defines coordinate system for XR world
- Types:
  - `viewer`: Relative to user's viewpoint
  - `local`: Relative to device origin
  - `local-floor`: Local space with floor at y=0
  - `bounded-floor`: Room-scale with boundaries
  - `unbounded`: No boundaries, world-scale

#### 3. XR Frame
- Each animation frame in XR
- Contains pose data for viewers and controllers
- Accessed via `XRSession.requestAnimationFrame()`

#### 4. XR Input Sources
- Controllers, gaze, hand tracking
- Accessed via `XRInputSource`
- Have gamepad, targetedRay, and profiles

### Important APIs

```javascript
// Check XR support
if (navigator.xr) {
  // WebXR is available
}

// Request a session
const session = await navigator.xr.requestSession('immersive-vr', {
  requiredFeatures: ['local-floor']
});

// Get viewer pose
const frame = await session.requestAnimationFrame(cb);
const pose = frame.getViewerPose(referenceSpace);
```

### Safety Considerations
- Always check user comfort (motion sickness)
- Provide seated/standing options
- Include exit mechanisms
- Warn about spatial requirements
- Consider frame rate for comfort (72-90fps ideal)

### Performance Tips
- Use WebGL optimizations
- Limit draw calls
- Use texture atlases
- Consider foveated rendering when available
- Profile on target devices

### Common Pitfalls
- Not handling session end events
- Ignoring frame rate drops
- Not testing on actual devices
- Forgetting to request permissions
- Not providing non-XR fallback
