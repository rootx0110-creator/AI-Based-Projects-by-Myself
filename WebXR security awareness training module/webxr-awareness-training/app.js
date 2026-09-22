/* ========================================
   WebXR Awareness Training Module
   Main Application JavaScript
   ======================================== */

// Utility Functions - defined first to avoid hoisting issues
function generateUserId() {
    return 'USR_' + Math.random().toString(36).substring(2, 10).toUpperCase();
}

function generateTimestamp() {
    return new Date().toLocaleString();
}

function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
}

// Application State
const AppState = {
    user: {
        id: generateUserId(),
        startedAt: Date.now(),
        completedModules: []
    },
    training: {
        currentModule: null,
        currentLesson: 0,
        modules: {},
        currentQuiz: null,
        quizAnswers: {},
        quizResults: []
    },
    ui: {
        currentView: 'dashboard',
        sidebarOpen: false
    },
    session: {
        startTime: Date.now(),
        totalTimeSpent: 0,
        xpEarned: 0,
        achievements: []
    }
};

// Training Modules Data
const MODULES = [
    {
        id: 'basics',
        title: 'WebXR Fundamentals',
        description: 'Learn the core concepts of WebXR and how it enables VR/AR in browsers.',
        icon: 'VR',
        iconClass: 'basic',
        color: '#00fff5',
        lessons: [
            {
                title: 'What is WebXR?',
                content: `
                    <p class="lesson-text">
                        <strong>WebXR</strong> is a web standard that enables Virtual Reality (VR) and 
                        Augmented Reality (AR) experiences directly in web browsers. It replaces the older 
                        WebVR standard with a more comprehensive and future-proof API.
                    </p>
                    <div class="lesson-highlight">
                        <p>WebXR allows developers to create immersive 3D experiences that work across 
                        different devices - from VR headsets to AR-enabled smartphones - using standard 
                        web technologies.</p>
                    </div>
                    <p class="lesson-text">
                        The API provides access to XR devices through the <code>navigator.xr</code> object, 
                        allowing you to create immersive sessions, track user movement, and render 3D content 
                        that responds to the user's position and orientation.
                    </p>
                    <div class="code-block">
                        <pre><code><span class="code-comment">// Check if WebXR is supported</span>
<span class="code-keyword">if</span> (navigator.xr) {
    <span class="code-comment">// WebXR is available on this device!</span>
    <span class="code-keyword">const</span> isSupported = <span class="code-keyword">await</span> navigator.xr.isSessionSupported(<span class="code-string">'immersive-vr'</span>);
}</code></pre>
                    </div>
                    <p class="lesson-text">
                        WebXR is supported in Chrome, Edge, and some experimental builds of other browsers. 
                        Always check for support before attempting to use the API.
                    </p>
                `
            },
            {
                title: 'XR Session Types',
                content: `
                    <p class="lesson-text">
                        WebXR supports different types of sessions depending on the experience you want to create:
                    </p>
                    <p class="lesson-text">
                        <strong>1. Immersive VR (<code>immersive-vr</code>)</strong><br>
                        Fully immersive virtual reality experience. The user is completely surrounded by 
                        virtual content and sees nothing of the real world.
                    </p>
                    <p class="lesson-text">
                        <strong>2. Immersive AR (<code>immersive-ar</code>)</strong><br>
                        Augmented reality experience where virtual content is overlaid on the real world. 
                        Used with AR headsets, transparent glasses, or video passthrough on VR devices.
                    </p>
                    <p class="lesson-text">
                        <strong>3. Inline (<code>inline</code>)</strong><br>
                        Non-immersive experience rendered in a regular HTML element. Used for 3D viewers, 
                        product configurators, or when XR hardware is not available.
                    </p>
                    <div class="lesson-highlight">
                        <p>Choosing the right session type is crucial for your application. Consider your 
                        target audience, the content you want to show, and the hardware available.</p>
                    </div>
                `
            },
            {
                title: 'Browser Support & Requirements',
                content: `
                    <p class="lesson-text">
                        WebXR support varies across browsers and devices. Here's what you need to know:
                    </p>
                    <ul class="lesson-text">
                        <li><strong>Chrome</strong> - Full WebXR support on desktop and Android</li>
                        <li><strong>Edge</strong> - Full WebXR support on Windows with compatible hardware</li>
                        <li><strong>Firefox</strong> - Limited/experimental support</li>
                        <li><strong>Safari</strong> - No WebXR support yet (use WebXR polyfills)</li>
                    </ul>
                    <div class="lesson-highlight">
                        <p>Always provide a fallback experience for users without WebXR support. 
                        An inline 3D viewer or informational page can serve as an alternative.</p>
                    </div>
                    <p class="lesson-text">
                        Hardware requirements vary: VR headsets need sensors for tracking, AR devices 
                        need cameras and depth sensors. Test on actual devices when possible.
                    </p>
                `
            }
        ],
        quiz: [
            {
                question: 'What does WebXR stand for?',
                options: [
                    'Web Extended Reality',
                    'Web XRetail',
                    'Web XML Reader',
                    'Web X-Ray'
                ],
                correct: 0,
                explanation: 'WebXR stands for Web Extended Reality, encompassing both VR and AR on the web.'
            },
            {
                question: 'Which of the following is NOT a valid WebXR session type?',
                options: [
                    'immersive-vr',
                    'immersive-ar',
                    'inline',
                    'immersive-mr'
                ],
                correct: 3,
                explanation: '"immersive-mr" is not a standard WebXR session type. The standard types are immersive-vr, immersive-ar, and inline.'
            },
            {
                question: 'How do you check if WebXR is supported in a browser?',
                options: [
                    'Check if window.XR exists',
                    'Check if navigator.xr exists',
                    'Check if document.xr exists',
                    'WebXR is always supported'
                ],
                correct: 1,
                explanation: 'You check for WebXR support by verifying if navigator.xr exists.'
            },
            {
                question: 'What is the purpose of an inline session?',
                options: [
                    'To create fully immersive VR',
                    'To overlay AR on the real world',
                    'To render 3D content in a regular HTML element',
                    'To connect to XR servers'
                ],
                correct: 2,
                explanation: 'Inline sessions render 3D content in standard HTML elements, useful for 3D viewers without XR hardware.'
            },
            {
                question: 'Which browser has FULL WebXR support?',
                options: [
                    'Safari',
                    'Firefox',
                    'Chrome',
                    'Internet Explorer'
                ],
                correct: 2,
                explanation: 'Chrome has full WebXR support on both desktop and Android platforms.'
            }
        ]
    },
    {
        id: 'sessions',
        title: 'XR Session Management',
        description: 'Master the art of creating and managing WebXR sessions.',
        icon: 'XRS',
        iconClass: 'session',
        color: '#00d4ff',
        lessons: [
            {
                title: 'Creating an XR Session',
                content: `
                    <p class="lesson-text">
                        To create an XR session, you use the <code>navigator.xr.requestSession()</code> method. 
                        This returns a promise that resolves to an <code>XRSession</code> object.
                    </p>
                    <div class="code-block">
                        <pre><code><span class="code-comment">// Request an immersive VR session</span>
<span class="code-keyword">const</span> session = <span class="code-keyword">await</span> navigator.xr.requestSession(<span class="code-string">'immersive-vr'</span>, {
    <span class="code-keyword">requiredFeatures</span>: [<span class="code-string">'local-floor'</span>],
    <span class="code-keyword">optionalFeatures</span>: [<span class="code-string">'bounded-floor'</span>, <span class="code-string">'hand-tracking'</span>]
});

<span class="code-comment">// Handle session end</span>
session.addEventListener(<span class="code-string">'end'</span>, <span class="code-keyword">onSessionEnd</span>);</code></pre>
                    </div>
                    <p class="lesson-text">
                        The <code>requiredFeatures</code> array specifies features that MUST be available 
                        for the session to start. If these aren't available, the request will fail.
                    </p>
                    <div class="lesson-highlight">
                        <p>Always handle the 'end' event to clean up resources when the user exits 
                        the XR experience. This includes stopping render loops and releasing resources.</p>
                    </div>
                `
            },
            {
                title: 'Session Lifecycle',
                content: `
                    <p class="lesson-text">
                        An XR session goes through several states during its lifecycle:
                    </p>
                    <p class="lesson-text">
                        <strong>1. Requesting</strong> - The browser prompts the user for permission 
                        and checks hardware availability.
                    </p>
                    <p class="lesson-text">
                        <strong>2. Active</strong> - The session is running, frames are being rendered, 
                        and XR pose data is available.
                    </p>
                    <p class="lesson-text">
                        <strong>3. Paused</strong> - The session is temporarily suspended (e.g., 
                        when the headset is removed). Rendering should pause.
                    </p>
                    <p class="lesson-text">
                        <strong>4. Ended</strong> - The session has ended. Clean up all XR resources.
                    </p>
                    <div class="code-block">
                        <pre><code><span class="code-comment">// Monitor session state changes</span>
session.addEventListener(<span class="code-string">'visibilitychange'</span>, () => {
    <span class="code-keyword">if</span> (session.visibilityState === <span class="code-string">'hidden'</span>) {
        <span class="code-comment">// Pause rendering</span>
        <span class="code-keyword">pauseRenderLoop</span>();
    } <span class="code-keyword">else</span> {
        <span class="code-comment">// Resume rendering</span>
        <span class="code-keyword">resumeRenderLoop</span>();
    }
});</code></pre>
                    </div>
                `
            },
            {
                title: 'Session Features',
                content: `
                    <p class="lesson-text">
                        WebXR sessions can request various features depending on your needs:
                    </p>
                    <p class="lesson-text">
                        <strong>Local Space (<code>local</code>)</strong> - Content positioned relative 
                        to the device's initial position.
                    </p>
                    <p class="lesson-text">
                        <strong>Local Floor (<code>local-floor</code>)</strong> - Like local space, 
                        but with the origin at floor level (y=0).
                    </p>
                    <p class="lesson-text">
                        <strong>Bounded Floor (<code>bounded-floor</code>)</strong> - Provides room-scale 
                        boundaries in addition to floor-level positioning.
                    </p>
                    <p class="lesson-text">
                        <strong>Hand Tracking (<code>hand-tracking</code>)</strong> - Enables hand 
                        gesture recognition without controllers.
                    </p>
                    <div class="lesson-highlight">
                        <p>Request only the features you actually need. Unnecessary features can limit 
                        compatibility with different devices.</p>
                    </div>
                `
            }
        ],
        quiz: [
            {
                question: 'Which method is used to create an XR session?',
                options: [
                    'navigator.xr.createSession()',
                    'navigator.xr.requestSession()',
                    'navigator.xr.startSession()',
                    'XR.createSession()'
                ],
                correct: 1,
                explanation: 'navigator.xr.requestSession() is the correct method to create an XR session.'
            },
            {
                question: 'What happens if a required feature is not available?',
                options: [
                    'The session starts without that feature',
                    'The session request fails',
                    'The browser substitutes a similar feature',
                    'The feature is silently ignored'
                ],
                correct: 1,
                explanation: 'If a required feature is not available, the session request will fail.'
            },
            {
                question: 'Which event fires when an XR session ends?',
                options: [
                    'close',
                    'finish',
                    'end',
                    'terminate'
                ],
                correct: 2,
                explanation: 'The "end" event fires when an XR session ends, allowing cleanup.'
            },
            {
                question: 'What is the local-floor reference space?',
                options: [
                    'Content positioned at device origin',
                    'Content positioned with floor at y=0',
                    'Content bounded by room walls',
                    'Content that follows the user'
                ],
                correct: 1,
                explanation: 'local-floor places the origin at floor level (y=0) for comfort standing experiences.'
            },
            {
                question: 'When should you pause your render loop?',
                options: [
                    'Never, always render',
                    'When the session visibility changes to hidden',
                    'Only when the user removes the headset',
                    'Every 5 seconds'
                ],
                correct: 1,
                explanation: 'Pause rendering when session visibilityState becomes "hidden" to save resources.'
            }
        ]
    },
    {
        id: 'spaces',
        title: 'Reference Spaces',
        description: 'Understand coordinate systems and spatial references in WebXR.',
        icon: 'REF',
        iconClass: 'reference',
        color: '#7b2cbf',
        lessons: [
            {
                title: 'Understanding Reference Spaces',
                content: `
                    <p class="lesson-text">
                        Reference spaces define the coordinate system used in WebXR. They determine 
                        how positions and orientations are interpreted in 3D space.
                    </p>
                    <p class="lesson-text">
                        Every object's position in XR is relative to a reference space. Choosing the 
                        right reference space is essential for proper content placement.
                    </p>
                    <div class="code-block">
                        <pre><code><span class="code-comment">// Get the reference space for the session</span>
<span class="code-keyword">const</span> referenceSpace = <span class="code-keyword">await</span> session.requestReferenceSpace(<span class="code-string">'local-floor'</span>);

<span class="code-comment">// Get viewer pose relative to reference space</span>
<span class="code-keyword">const</span> frame = <span class="code-keyword">await</span> session.requestAnimationFrame(<span class="code-keyword">frameCallback</span>);
<span class="code-keyword">const</span> pose = frame.getViewerPose(referenceSpace);</code></pre>
                    </div>
                `
            },
            {
                title: 'Types of Reference Spaces',
                content: `
                    <p class="lesson-text">
                        WebXR provides several reference space types for different use cases:
                    </p>
                    <p class="lesson-text">
                        <strong>Viewer (<code>viewer</code>)</strong> - Relative to the user's current 
                        viewpoint. Moves with the user. Best for HUD elements and UI.
                    </p>
                    <p class="lesson-text">
                        <strong>Local (<code>local</code>)</strong> - Relative to the device's initial 
                        position. Good for small experiences that stay in one place.
                    </p>
                    <p class="lesson-text">
                        <strong>Local Floor (<code>local-floor</code>)</strong> - Like local, but Y=0 
                        is at floor level. Ideal for standing experiences.
                    </p>
                    <p class="lesson-text">
                        <strong>Bounded Floor (<code>bounded-floor</code>)</strong> - Includes physical 
                        room boundaries for room-scale experiences.
                    </p>
                    <p class="lesson-text">
                        <strong>Unbounded (<code>unbounded</code>)</strong> - No positional limits. 
                        For large-scale world experiences (requires specific hardware).
                    </p>
                    <div class="lesson-highlight">
                        <p>For most applications, <code>local-floor</code> is the best choice as it 
                        provides a stable floor reference for standing experiences.</p>
                    </div>
                `
            },
            {
                title: 'Working with Poses',
                content: `
                    <p class="lesson-text">
                        Poses provide position and orientation data for viewers and input sources. 
                        They are obtained from XR frames during the render loop.
                    </p>
                    <div class="code-block">
                        <pre><code><span class="code-keyword">function</span> <span class="code-function">frameCallback</span>(time, frame) {
    <span class="code-comment">// Get the viewer's pose</span>
    <span class="code-keyword">const</span> pose = frame.getViewerPose(referenceSpace);
    
    <span class="code-keyword">if</span> (pose) {
        <span class="code-comment">// Access position and orientation</span>
        <span class="code-keyword">const</span> position = pose.transform.position;
        <span class="code-keyword">const</span> orientation = pose.transform.orientation;
        
        <span class="code-comment">// Render the scene from this viewpoint</span>
        renderScene(position, orientation);
    }
    
    <span class="code-keyword">return</span> session.requestAnimationFrame(frameCallback);
}</code></pre>
                    </div>
                    <p class="lesson-text">
                        The pose's transform contains a 3D position (x, y, z) and orientation (quaternion). 
                        Use these to position your camera and render the scene correctly.
                    </p>
                `
            }
        ],
        quiz: [
            {
                question: 'What does a reference space define?',
                options: [
                    'The browser compatibility',
                    'The coordinate system for XR',
                    'The session hardware',
                    'The 3D model format'
                ],
                correct: 1,
                explanation: 'A reference space defines the coordinate system used to interpret positions in XR.'
            },
            {
                question: 'Which reference space moves with the user?',
                options: [
                    'local',
                    'local-floor',
                    'viewer',
                    'bounded-floor'
                ],
                correct: 2,
                explanation: 'The viewer reference space is relative to the user current viewpoint and moves with them.'
            },
            {
                question: 'What is the benefit of local-floor over local?',
                options: [
                    'It provides room boundaries',
                    'It positions Y=0 at floor level',
                    'It moves with the user',
                    'It is faster to compute'
                ],
                correct: 1,
                explanation: 'local-floor positions the origin at floor level (y=0), making it ideal for standing experiences.'
            },
            {
                question: 'How do you obtain pose data in WebXR?',
                options: [
                    'From the session object directly',
                    'From XR frames during the animation loop',
                    'From the reference space',
                    'From the DOM element'
                ],
                correct: 1,
                explanation: 'Pose data is obtained from XR frames during the requestAnimationFrame callback.'
            },
            {
                question: 'Which reference space is best for room-scale experiences?',
                options: [
                    'viewer',
                    'local',
                    'bounded-floor',
                    'unbounded'
                ],
                correct: 2,
                explanation: 'bounded-floor provides room-scale boundaries along with floor-level positioning.'
            }
        ]
    },
    {
        id: 'input',
        title: 'Input Sources',
        description: 'Learn about controllers, gaze input, and interaction in WebXR.',
        icon: 'INPT',
        iconClass: 'input',
        color: '#ff00ff',
        lessons: [
            {
                title: 'XR Input Sources Overview',
                content: `
                    <p class="lesson-text">
                        XR input sources represent devices that can interact with your experience - 
                        controllers, hands, gaze, and more.
                    </p>
                    <p class="lesson-text">
                        Input sources are accessed through the session and provide information about 
                        their position, orientation, and capabilities.
                    </p>
                    <div class="code-block">
                        <pre><code><span class="code-comment">// Get input sources from the session</span>
<span class="code-keyword">const</span> inputSources = session.inputSources;

<span class="code-keyword">for</span> (<span class="code-keyword">const</span> source <span class="code-keyword">of</span> inputSources) {
    <span class="code-keyword">const</span> profile = source.profiles[0];
    <span class="code-keyword">const</span> handedness = source.handedness;
    <span class="code-keyword">console</span>.<span class="code-function">log</span>(<span class="code-string">'Input: '</span> + profile + <span class="code-string">', '</span> + handedness);
}</code></pre>
                    </div>
                `
            },
            {
                title: 'Controllers and Gamepads',
                content: `
                    <p class="lesson-text">
                        Controllers provide button, trigger, and axis input for interaction. 
                        They are accessed through the gamepad property of an input source.
                    </p>
                    <div class="code-block">
                        <pre><code><span class="code-keyword">function</span> <span class="code-function">processInput</span>(inputSource) {
    <span class="code-keyword">const</span> gamepad = inputSource.gamepad;
    
    <span class="code-keyword">if</span> (gamepad) {
        <span class="code-comment">// Read button states</span>
        <span class="code-keyword">const</span> triggerPressed = gamepad.buttons[0].pressed;
        <span class="code-keyword">const</span> gripPressed = gamepad.buttons[1].pressed;
        
        <span class="code-comment">// Read axis values (thumbstick)</span>
        <span class="code-keyword">const</span> thumbX = gamepad.axes[0];
        <span class="code-keyword">const</span> thumbY = gamepad.axes[1];
        
        <span class="code-comment">// Process input...</span>
    }
}</code></pre>
                    </div>
                    <div class="lesson-highlight">
                        <p>Button indices and meanings vary by controller profile. Always check the 
                        profile to understand which button is which.</p>
                    </div>
                `
            },
            {
                title: 'Gaze and Ray Input',
                content: `
                    <p class="lesson-text">
                        Some input methods use gaze (where the user looks) or rays for interaction. 
                        The targetedRay property provides a ray for hit testing.
                    </p>
                    <div class="code-block">
                        <pre><code><span class="code-keyword">function</span> <span class="code-function">getGazeTarget</span>(inputSource, referenceSpace) {
    <span class="code-keyword">const</span> ray = inputSource.targetedRay;
    
    <span class="code-keyword">if</span> (ray) {
        <span class="code-comment">// Get the ray pose in the reference space</span>
        <span class="code-keyword">const</span> pose = ray.getPose(referenceSpace);
        
        <span class="code-keyword">if</span> (pose) {
            <span class="code-keyword">const</span> origin = pose.transform.position;
            <span class="code-keyword">const</span> direction = pose.transform.orientation;
            
            <span class="code-comment">// Use for raycasting/hit testing...</span>
            <span class="code-keyword">return</span> { origin, direction };
        }
    }
    <span class="code-keyword">return</span> <span class="code-keyword">null</span>;
}</code></pre>
                    </div>
                    <p class="lesson-text">
                        Gaze input is common in mobile VR (where the phone position represents gaze direction) 
                        and can be used for simple selection interfaces.
                    </p>
                `
            }
        ],
        quiz: [
            {
                question: 'Where are input sources stored in an XR session?',
                options: [
                    'session.sources',
                    'session.inputSources',
                    'session.controllers',
                    'session.devices'
                ],
                correct: 1,
                explanation: 'Input sources are accessed through the session.inputSources array.'
            },
            {
                question: 'How do you read button state from a controller?',
                options: [
                    'inputSource.buttons',
                    'inputSource.gamepad.buttons',
                    'inputSource.trigger',
                    'inputSource.input'
                ],
                correct: 1,
                explanation: 'Controller buttons are accessed through inputSource.gamepad.buttons array.'
            },
            {
                question: 'What property provides ray information for gaze input?',
                options: [
                    'inputSource.gaze',
                    'inputSource.ray',
                    'inputSource.targetedRay',
                    'inputSource.pointer'
                ],
                correct: 2,
                explanation: 'The targetedRay property provides ray information for gaze and pointer input.'
            },
            {
                question: 'What does the handedness property tell you?',
                options: [
                    'How many hands the controller supports',
                    'Whether it left or right hand controller',
                    'Which hand the user prefers',
                    'The grip strength'
                ],
                correct: 1,
                explanation: 'The handedness property indicates whether the input source is a left or right hand device.'
            },
            {
                question: 'Why should you check controller profiles?',
                options: [
                    'To determine battery level',
                    'To understand button mappings for different controllers',
                    'To check if the controller is connected',
                    'To determine the price of the controller'
                ],
                correct: 1,
                explanation: 'Different controllers have different button layouts, so profiles help understand the mapping.'
            }
        ]
    },
    {
        id: 'safety',
        title: 'Safety & Best Practices',
        description: 'Ensure user comfort and safety in WebXR experiences.',
        icon: 'SAFE',
        iconClass: 'safety',
        color: '#ff6b35',
        lessons: [
            {
                title: 'User Comfort & Motion Sickness',
                content: `
                    <p class="lesson-text">
                        Motion sickness is one of the biggest challenges in XR development. 
                        Understanding its causes helps you create comfortable experiences.
                    </p>
                    <p class="lesson-text">
                        <strong>Common causes of motion sickness:</strong>
                    </p>
                    <ul class="lesson-text">
                        <li>Vection (feeling motion when stationary)</li>
                        <li>Latency between head movement and visual update</li>
                        <li>Artificial camera movement (walking without moving)</li>
                        <li>Low frame rates</li>
                        <li>Poor alignment between visual and vestibular systems</li>
                    </ul>
                    <div class="lesson-highlight">
                        <p>Best practice: Avoid artificial locomotion in early experiences. Let users 
                        move physically or use teleportation for movement.</p>
                    </div>
                `
            },
            {
                title: 'Comfort Options & Settings',
                content: `
                    <p class="lesson-text">
                        Give users control over their experience to maximize comfort:
                    </p>
                    <p class="lesson-text">
                        <strong>1. Seated/Standing Mode</strong> - Allow users to choose their 
                        preferred mode based on their physical setup.
                    </p>
                    <p class="lesson-text">
                        <strong>2. Movement Options</strong> - Provide teleportation, snap turning, 
                        and vignette options for locomotion.
                    </p>
                    <p class="lesson-text">
                        <strong>3. Seated Experience</strong> - Always offer a seated alternative 
                        for experiences that could be intense.
                    </p>
                    <p class="lesson-text">
                        <strong>4. Adjustable Settings</strong> - Let users adjust field of view, 
                        movement speed, and comfort settings.
                    </p>
                    <div class="code-block">
                        <pre><code><span class="code-comment">// Example comfort settings UI</span>
<span class="code-keyword">const</span> comfortSettings = {
    movementMode: <span class="code-string">'teleport'</span>, <span class="code-comment">// or 'smooth'</span>
    turnStyle: <span class="code-string">'snap'</span>, <span class="code-comment">// or 'smooth'</span>
    vignetteEnabled: <span class="code-keyword">true</span>,
    seatedMode: <span class="code-keyword">false</span>
};</code></pre>
                    </div>
                `
            },
            {
                title: 'Accessibility & Inclusive Design',
                content: `
                    <p class="lesson-text">
                        Make your XR experiences accessible to as many users as possible:
                    </p>
                    <p class="lesson-text">
                        <strong>Color Vision</strong> - Don't rely solely on color to convey 
                        information. Use shapes, patterns, and labels too.
                    </p>
                    <p class="lesson-text">
                        <strong>Motion Sensitivity</strong> - Provide comfort options and respect 
                        user preferences for reduced motion.
                    </p>
                    <p class="lesson-text">
                        <strong>Alternative Input</strong> - Support multiple input methods including 
                        gaze, voice, and keyboard where possible.
                    </p>
                    <p class="lesson-text">
                        <strong>Clear Instructions</strong> - Provide clear onboarding and instructions. 
                        Not all users are familiar with XR conventions.
                    </p>
                    <div class="lesson-highlight">
                        <p>Remember: The best XR experience is one that anyone can enjoy safely. 
                        Test with diverse users and gather feedback.</p>
                    </div>
                `
            }
        ],
        quiz: [
            {
                question: 'What is vection in the context of VR?',
                options: [
                    'Visual detection technology',
                    'The illusion of self-motion',
                    'Virtual object selection',
                    'Video frame rate'
                ],
                correct: 1,
                explanation: 'Vection is the illusion of self-motion when visually moving but physically stationary, a common cause of VR discomfort.'
            },
            {
                question: 'Which locomotion method is generally more comfortable?',
                options: [
                    'Smooth continuous movement',
                    'Teleportation',
                    'Flying',
                    'Being pushed by forces'
                ],
                correct: 1,
                explanation: 'Teleportation is generally more comfortable as it avoids the visual-vestibular conflict of smooth movement.'
            },
            {
                question: 'Why should you offer a seated mode?',
                options: [
                    'It is cheaper to develop',
                    'Some users cannot stand for long periods',
                    'It uses less battery',
                    'Standing is not allowed in VR'
                ],
                correct: 1,
                explanation: 'Seated mode makes experiences accessible to users who cannot or prefer not to stand.'
            },
            {
                question: 'What is a good practice for color-coded information?',
                options: [
                    'Use only bright colors',
                    'Add shapes, patterns, or labels as alternatives',
                    'Use as many colors as possible',
                    'Avoid color entirely'
                ],
                correct: 1,
                explanation: 'Adding shapes, patterns, or labels ensures information is accessible regardless of color vision.'
            },
            {
                question: 'What is the ideal frame rate for comfortable VR?',
                options: [
                    '30 FPS',
                    '60 FPS',
                    '72-90 FPS or higher',
                    '15 FPS'
                ],
                correct: 2,
                explanation: '72-90 FPS or higher is ideal for comfortable VR to minimize latency and motion sickness.'
            }
        ]
    }
];

// Achievements Data
const ACHIEVEMENTS = [
    {
        id: 'first_module',
        name: 'First Steps',
        description: 'Complete your first training module',
        icon: 'M'
    },
    {
        id: 'all_modules',
        name: 'WebXR Master',
        description: 'Complete all training modules',
        icon: 'W'
    },
    {
        id: 'quiz_perfect',
        name: 'Perfect Score',
        description: 'Get 100% on any quiz',
        icon: 'P'
    },
    {
        id: 'quiz_master',
        name: 'Quiz Champion',
        description: 'Pass all quizzes with 80% or higher',
        icon: 'Q'
    },
    {
        id: 'xp_100',
        name: 'Rising Star',
        description: 'Earn 100 XP',
        icon: 'X'
    },
    {
        id: 'xp_500',
        name: 'VR Veteran',
        description: 'Earn 500 XP',
        icon: 'V'
    }
];

// DOM Elements
const DOM = {
    sidebar: document.getElementById('sidebar'),
    navItems: document.querySelectorAll('.nav-item'),
    headerTitle: document.getElementById('headerTitle'),
    headerSubtitle: document.getElementById('headerSubtitle'),
    views: {
        dashboard: document.getElementById('dashboardView'),
        modules: document.getElementById('modulesView'),
        lesson: document.getElementById('lessonView'),
        quiz: document.getElementById('quizView'),
        reports: document.getElementById('reportsView')
    },
    xpDisplay: document.getElementById('xpDisplay'),
    modulesComplete: document.getElementById('modulesComplete'),
    totalXp: document.getElementById('totalXp'),
    completionRate: document.getElementById('completionRate'),
    trainingTime: document.getElementById('trainingTime'),
    progressPercent: document.getElementById('progressPercent'),
    modulesCount: document.getElementById('modulesCount'),
    quizAccuracy: document.getElementById('quizAccuracy'),
    lessonsCount: document.getElementById('lessonsCount'),
    modulesBar: document.getElementById('modulesBar'),
    quizBar: document.getElementById('quizBar'),
    lessonsBar: document.getElementById('lessonsBar'),
    modulesList: document.getElementById('modulesList'),
    allModulesGrid: document.getElementById('allModulesGrid'),
    achievementsGrid: document.getElementById('achievementsGrid'),
    achievementsCount: document.getElementById('achievementsCount'),
    resetBtn: document.getElementById('resetBtn'),
    toastContainer: document.getElementById('toastContainer'),
    // Lesson elements
    lessonBackBtn: document.getElementById('lessonBackBtn'),
    lessonContent: document.getElementById('lessonContent'),
    lessonProgressText: document.getElementById('lessonProgressText'),
    lessonMiniBar: document.getElementById('lessonMiniBar'),
    lessonPrevBtn: document.getElementById('lessonPrevBtn'),
    lessonNextBtn: document.getElementById('lessonNextBtn'),
    // Quiz elements
    quizModuleName: document.getElementById('quizModuleName'),
    quizQuestionCount: document.getElementById('quizQuestionCount'),
    quizProgressBar: document.getElementById('quizProgressBar'),
    quizContent: document.getElementById('quizContent'),
    quizPrevBtn: document.getElementById('quizPrevBtn'),
    quizSubmitBtn: document.getElementById('quizSubmitBtn')
};

// State Management
function loadState() {
    try {
        const savedState = localStorage.getItem('webxr_training_state');
        if (savedState) {
            const parsed = JSON.parse(savedState);
            console.log('Loaded saved state:', parsed.user?.id);
            Object.assign(AppState, parsed);
        } else {
            console.log('No saved state found, using defaults');
        }
    } catch (e) {
        console.warn('localStorage not available (file:// protocol?), using in-memory state:', e.message);
        // State already has defaults, so we're fine
    }
}

function saveState() {
    try {
        localStorage.setItem('webxr_training_state', JSON.stringify(AppState));
        console.log('State saved to localStorage');
    } catch (e) {
        console.warn('Could not save to localStorage:', e.message);
    }
}

// Initialize State for Modules
function initializeModuleState() {
    MODULES.forEach(module => {
        if (!AppState.training.modules[module.id]) {
            AppState.training.modules[module.id] = {
                completed: false,
                quizScore: null,
                attempts: 0,
                lessonsCompleted: 0,
                lastAccessed: null
            };
        }
    });
}

// Calculate Progress
function calculateProgress() {
    const totalModules = MODULES.length;
    const completedModules = AppState.user.completedModules.length;
    const progress = totalModules > 0 ? (completedModules / totalModules) * 100 : 0;
    
    let totalLessons = 0;
    let completedLessons = 0;
    let totalQuizScore = 0;
    let quizCount = 0;
    
    MODULES.forEach(module => {
        totalLessons += module.lessons.length;
        completedLessons += AppState.training.modules[module.id].lessonsCompleted;
        if (AppState.training.modules[module.id].quizScore !== null) {
            totalQuizScore += AppState.training.modules[module.id].quizScore;
            quizCount++;
        }
    });
    
    const quizAccuracy = quizCount > 0 ? totalQuizScore / quizCount : 0;
    const lessonProgress = totalLessons > 0 ? (completedLessons / totalLessons) * 100 : 0;
    
    return {
        moduleProgress: progress,
        completedModules,
        totalModules,
        lessonProgress,
        completedLessons,
        totalLessons,
        quizAccuracy,
        xp: AppState.session.xpEarned,
        timeSpent: AppState.session.totalTimeSpent
    };
}

// Update UI with Progress
function updateProgressUI() {
    const progress = calculateProgress();
    
    DOM.xpDisplay.textContent = progress.xp;
    DOM.modulesComplete.textContent = `${progress.completedModules}/${progress.totalModules}`;
    DOM.totalXp.textContent = progress.xp;
    DOM.completionRate.textContent = `${Math.round(progress.moduleProgress)}%`;
    DOM.trainingTime.textContent = `${Math.floor(progress.timeSpent / 60)}m`;
    DOM.progressPercent.textContent = `${Math.round(progress.moduleProgress)}%`;
    DOM.modulesCount.textContent = `${progress.completedModules}/${progress.totalModules}`;
    DOM.quizAccuracy.textContent = `${Math.round(progress.quizAccuracy)}%`;
    DOM.lessonsCount.textContent = progress.completedLessons;
    
    DOM.modulesBar.style.width = `${progress.moduleProgress}%`;
    DOM.quizBar.style.width = `${progress.quizAccuracy}%`;
    DOM.lessonsBar.style.width = `${progress.lessonProgress}%`;
    
    updateModulesPreview();
    updateAchievements();
}

// Render Modules Preview
function updateModulesPreview() {
    DOM.modulesList.innerHTML = MODULES.map(module => {
        const state = AppState.training.modules[module.id];
        const isCompleted = state.completed;
        const isUnlocked = AppState.user.completedModules.length === 0 || 
            AppState.user.completedModules.includes(module.id) ||
            MODULES.indexOf(module) <= AppState.user.completedModules.length;
        
        let iconClass = 'locked';
        let statusClass = '';
        let statusText = 'Not Started';
        
        if (isCompleted) {
            iconClass = 'completed';
            statusClass = 'completed';
            statusText = 'Completed';
        } else if (isUnlocked) {
            iconClass = 'active';
            statusText = 'In Progress';
        }
        
        return `
            <div class="module-preview-item" data-module="${module.id}">
                <div class="module-preview-icon ${iconClass}">${module.icon}</div>
                <div class="module-preview-info">
                    <div class="module-preview-name">${module.title}</div>
                    <div class="module-preview-status ${statusClass}">${statusText}</div>
                </div>
            </div>
        `;
    }).join('');
    
    // Add click handlers
    DOM.modulesList.querySelectorAll('.module-preview-item').forEach(item => {
        item.addEventListener('click', () => {
            const moduleId = item.dataset.module;
            navigateToModule(moduleId);
        });
    });
}

// Render All Modules Grid
function renderAllModules() {
    DOM.allModulesGrid.innerHTML = MODULES.map((module, index) => {
        const state = AppState.training.modules[module.id];
        const isCompleted = state.completed;
        const isUnlocked = index === 0 || AppState.user.completedModules.includes(MODULES[index - 1].id);
        
        let cardClass = '';
        let statusHtml = '';
        let actionHtml = '';
        
        if (isCompleted) {
            cardClass = 'completed';
            statusHtml = '<span class="module-card-status completed"><span class="status-dot"></span> Completed</span>';
            actionHtml = '<span class="module-card-action">Review</span>';
        } else if (!isUnlocked) {
            statusHtml = '<span class="module-card-status"><span class="status-dot"></span> Locked</span>';
            actionHtml = '<span class="module-card-action" style="opacity: 0.5; cursor: not-allowed;">Complete Previous</span>';
        } else {
            statusHtml = '<span class="module-card-status"><span class="status-dot" style="background: var(--neon-cyan); box-shadow: 0 0 8px var(--neon-cyan);"></span> Available</span>';
            actionHtml = '<span class="module-card-action">Start Learning</span>';
        }
        
        return `
            <div class="module-card ${cardClass}" data-module="${module.id}">
                <div class="module-card-header">
                    <div class="module-card-icon ${module.iconClass}">${module.icon}</div>
                    <div class="module-card-info">
                        <h3>${module.title}</h3>
                        <p class="module-card-desc">${module.description}</p>
                    </div>
                </div>
                <div class="module-card-footer">
                    ${statusHtml}
                    ${actionHtml}
                </div>
            </div>
        `;
    }).join('');
    
    // Add click handlers
    DOM.allModulesGrid.querySelectorAll('.module-card').forEach(card => {
        card.addEventListener('click', () => {
            const moduleId = card.dataset.module;
            const index = MODULES.findIndex(m => m.id === moduleId);
            const isUnlocked = index === 0 || AppState.user.completedModules.includes(MODULES[index - 1].id);
            
            if (!isUnlocked) {
                showToast('info', 'Module Locked', 'Complete the previous module first.');
                return;
            }
            
            navigateToModule(moduleId);
        });
    });
}

// Render Achievements
function updateAchievements() {
    const unlockedCount = AppState.session.achievements.length;
    DOM.achievementsCount.textContent = `${unlockedCount}/${ACHIEVEMENTS.length}`;
    
    DOM.achievementsGrid.innerHTML = ACHIEVEMENTS.map(achievement => {
        const isUnlocked = AppState.session.achievements.includes(achievement.id);
        return `
            <div class="achievement-item ${isUnlocked ? 'unlocked' : 'locked'}">
                <div class="achievement-icon">${achievement.icon}</div>
                <span class="achievement-name">${achievement.name}</span>
            </div>
        `;
    }).join('');
}

// Check Achievements
function checkAchievements() {
    const progress = calculateProgress();
    
    // First module completed
    if (progress.completedModules >= 1 && !AppState.session.achievements.includes('first_module')) {
        unlockAchievement('first_module');
    }
    
    // All modules completed
    if (progress.completedModules === MODULES.length && !AppState.session.achievements.includes('all_modules')) {
        unlockAchievement('all_modules');
    }
    
    // Check quiz scores for perfect score
    MODULES.forEach(module => {
        const state = AppState.training.modules[module.id];
        if (state.quizScore === 100 && !AppState.session.achievements.includes('quiz_perfect')) {
            unlockAchievement('quiz_perfect');
        }
    });
    
    // Check for quiz master (all quizzes 80%+)
    let allQuizzesPassed = true;
    MODULES.forEach(module => {
        const state = AppState.training.modules[module.id];
        if (state.quizScore === null || state.quizScore < 80) {
            allQuizzesPassed = false;
        }
    });
    if (allQuizzesPassed && !AppState.session.achievements.includes('quiz_master')) {
        unlockAchievement('quiz_master');
    }
    
    // XP achievements
    if (progress.xp >= 100 && !AppState.session.achievements.includes('xp_100')) {
        unlockAchievement('xp_100');
    }
    if (progress.xp >= 500 && !AppState.session.achievements.includes('xp_500')) {
        unlockAchievement('xp_500');
    }
}

function unlockAchievement(id) {
    AppState.session.achievements.push(id);
    saveState();
    updateAchievements();
    showToast('success', 'Achievement Unlocked!', ACHIEVEMENTS.find(a => a.id === id).name);
}

// Navigation
function navigateToView(viewName) {
    console.log('navigateToView:', viewName);
    
    // Validate view name
    const validViews = ['dashboard', 'modules', 'lesson', 'quiz', 'reports'];
    if (!validViews.includes(viewName)) {
        console.error('Invalid view:', viewName);
        return;
    }
    
    // Check DOM elements
    if (!DOM.views[viewName]) {
        console.error('View element not found:', viewName, DOM.views[viewName]);
        return;
    }
    
    // Hide all views
    Object.values(DOM.views).forEach(view => {
        view.classList.remove('active');
    });
    
    // Show target view
    DOM.views[viewName].classList.add('active');
    
    // Update nav items
    DOM.navItems.forEach(item => {
        item.classList.remove('active');
        if (item.dataset.view === viewName) {
            item.classList.add('active');
        }
    });
    
    // Update header
    const titles = {
        dashboard: ['Dashboard', 'Welcome to WebXR Awareness Training'],
        modules: ['Training Modules', 'Select a module to begin learning'],
        lesson: ['Lesson', 'Interactive learning content'],
        quiz: ['Knowledge Quiz', 'Test your understanding'],
        reports: ['Reports', 'Download your progress reports']
    };
    
    DOM.headerTitle.textContent = titles[viewName][0];
    DOM.headerSubtitle.textContent = titles[viewName][1];
    
    AppState.ui.currentView = viewName;
    saveState();
}

function navigateToModule(moduleId) {
    const module = MODULES.find(m => m.id === moduleId);
    if (!module) return;
    
    AppState.training.currentModule = moduleId;
    AppState.training.currentLesson = 0;
    AppState.training.modules[moduleId].lastAccessed = Date.now();
    
    saveState();
    renderLesson();
    navigateToView('lesson');
}

// Lesson Functions
function renderLesson() {
    const moduleId = AppState.training.currentModule;
    const lessonIndex = AppState.training.currentLesson;
    const module = MODULES.find(m => m.id === moduleId);
    
    if (!module) {
        navigateToView('modules');
        return;
    }
    
    const lesson = module.lessons[lessonIndex];
    const totalLessons = module.lessons.length;
    
    // Update progress display
    DOM.lessonProgressText.textContent = `Lesson ${lessonIndex + 1}/${totalLessons}`;
    DOM.lessonMiniBar.style.width = `${((lessonIndex + 1) / totalLessons) * 100}%`;
    
    // Update buttons
    DOM.lessonPrevBtn.disabled = lessonIndex === 0;
    DOM.lessonNextBtn.textContent = lessonIndex === totalLessons - 1 ? 'Complete Lesson' : 'Next Lesson';
    
    // Render lesson content
    DOM.lessonContent.innerHTML = `
        <h1 class="lesson-title">${lesson.title}</h1>
        <p class="lesson-subtitle">Module: ${module.title}</p>
        ${lesson.content}
        ${lessonIndex === totalLessons - 1 ? `
            <div class="lesson-quiz-prompt">
                <h4>Ready to Test Your Knowledge?</h4>
                <p>Complete this lesson and take the quiz to earn XP</p>
                <button class="go-quiz-btn" id="goQuizFromLesson">Take Quiz Now</button>
            </div>
        ` : ''}
    `;
    
    // Add event listeners for lesson buttons
    DOM.lessonNextBtn.onclick = () => {
        if (lessonIndex === module.lessons.length - 1) {
            // Complete the module
            completeLesson();
        } else {
            AppState.training.currentLesson++;
            AppState.training.modules[moduleId].lessonsCompleted = AppState.training.currentLesson;
            saveState();
            renderLesson();
        }
    };
    
    // Quiz button from lesson
    const quizBtn = document.getElementById('goQuizFromLesson');
    if (quizBtn) {
        quizBtn.addEventListener('click', () => {
            startQuiz(moduleId);
        });
    }
}

function completeLesson() {
    const moduleId = AppState.training.currentModule;
    const module = MODULES.find(m => m.id === moduleId);
    console.log('completeLesson: moduleId =', moduleId, 'module =', module);
    
    if (!module) {
        console.error('completeLesson: module not found');
        return;
    }
    
    // Mark module as completed
    AppState.training.modules[moduleId].completed = true;
    AppState.training.modules[moduleId].lessonsCompleted = module.lessons.length;
    
    // Add to completed modules if not already
    if (!AppState.user.completedModules.includes(moduleId)) {
        AppState.user.completedModules.push(moduleId);
    }
    
    // Award XP
    const xpReward = 50;
    AppState.session.xpEarned += xpReward;
    
    saveState();
    updateProgressUI();
    checkAchievements();
    
    showToast('success', 'Lesson Complete!', `+${xpReward} XP earned!`);
    
    // Navigate to quiz or modules
    setTimeout(() => {
        startQuiz(moduleId);
    }, 1500);
}

// Quiz Functions
function startQuiz(moduleId) {
    console.log('startQuiz called with:', moduleId);
    const module = MODULES.find(m => m.id === moduleId);
    if (!module) {
        console.error('Module not found:', moduleId);
        return;
    }
    
    AppState.training.currentQuiz = moduleId;
    AppState.quizAnswers = {};
    AppState.quizResults = [];
    
    DOM.quizModuleName.textContent = module.title;
    DOM.quizQuestionCount.textContent = 'Question 1/' + module.quiz.length;
    DOM.quizProgressBar.style.width = '0%';
    
    renderQuizQuestion(0);
    navigateToView('quiz');
}

function renderQuizQuestion(questionIndex) {
    const moduleId = AppState.training.currentQuiz;
    const module = MODULES.find(m => m.id === moduleId);
    const question = module.quiz[questionIndex];
    
    DOM.quizQuestionCount.textContent = `Question ${questionIndex + 1}/${module.quiz.length}`;
    DOM.quizProgressBar.style.width = `${((questionIndex + 1) / module.quiz.length) * 100}%`;
    
    const selectedAnswer = AppState.quizAnswers[questionIndex];
    
    DOM.quizContent.innerHTML = `
        <p class="quiz-question">${question.question}</p>
        <div class="quiz-options">
            ${question.options.map((option, idx) => `
                <div class="quiz-option ${selectedAnswer === idx ? 'selected' : ''}" data-index="${idx}">
                    <div class="quiz-option-marker">
                        ${selectedAnswer === idx ? '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>' : ''}
                    </div>
                    <span class="quiz-option-text">${option}</span>
                </div>
            `).join('')}
        </div>
        <div class="quiz-feedback ${AppState.quizResults[questionIndex] ? 'show' : ''}" 
             class="${AppState.quizResults[questionIndex] === true ? 'correct' : 'incorrect'}">
            <h4>${AppState.quizResults[questionIndex] === true ? 'Correct!' : 'Incorrect'}</h4>
            <p>${question.explanation}</p>
        </div>
    `;
    
    // Add click handlers for options
    DOM.quizContent.querySelectorAll('.quiz-option').forEach(option => {
        option.addEventListener('click', () => {
            const index = parseInt(option.dataset.index);
            selectAnswer(questionIndex, index);
        });
    });
    
    // Update buttons
    const isLastQuestion = questionIndex === module.quiz.length - 1;
    DOM.quizSubmitBtn.textContent = isLastQuestion ? 'Submit Quiz' : 'Next Question';
    DOM.quizPrevBtn.disabled = questionIndex === 0;
    
    DOM.quizSubmitBtn.onclick = () => {
        if (isLastQuestion) {
            submitQuiz();
        } else {
            // Move to next question
            if (AppState.quizAnswers[questionIndex] !== undefined) {
                renderQuizQuestion(questionIndex + 1);
            } else {
                showToast('warning', 'Not Ready', 'Please select an answer before continuing.');
            }
        }
    };
    
    DOM.quizPrevBtn.onclick = () => {
        if (questionIndex > 0) {
            renderQuizQuestion(questionIndex - 1);
        }
    };
}

function selectAnswer(questionIndex, answerIndex) {
    AppState.quizAnswers[questionIndex] = answerIndex;
    renderQuizQuestion(questionIndex);
}

function submitQuiz() {
    const moduleId = AppState.training.currentQuiz;
    const module = MODULES.find(m => m.id === moduleId);
    
    // Grade the quiz
    let correctCount = 0;
    module.quiz.forEach((question, idx) => {
        if (AppState.quizAnswers[idx] === question.correct) {
            correctCount++;
            AppState.quizResults[idx] = true;
        } else {
            AppState.quizResults[idx] = false;
        }
    });
    
    const score = Math.round((correctCount / module.quiz.length) * 100);
    const state = AppState.training.modules[moduleId];
    state.quizScore = score;
    state.attempts++;
    
    saveState();
    
    // Show results
    showQuizResults(score, correctCount, module.quiz.length);
    
    // Award XP
    const xpReward = Math.round(score * 2);
    AppState.session.xpEarned += xpReward;
    saveState();
    updateProgressUI();
    checkAchievements();
    
    showToast('success', 'Quiz Complete!', `+${xpReward} XP earned!`);
}

function showQuizResults(score, correct, total) {
    const isPassing = score >= 70;
    const scoreClass = score === 100 ? 'perfect' : score >= 80 ? 'good' : score >= 60 ? 'ok' : 'poor';
    
    DOM.quizContent.innerHTML = `
        <div class="quiz-results">
            <h3 class="${isPassing ? 'pass' : 'fail'}">
                ${isPassing ? 'Congratulations!' : 'Keep Learning!'}
            </h3>
            <p style="color: var(--text-secondary); margin-bottom: 24px;">
                ${isPassing ? 'You demonstrated good understanding of this module.' : 'Review the material and try again.'}
            </p>
            <div class="quiz-score-display">
                <div class="quiz-score-item">
                    <span class="quiz-score-value ${scoreClass}">${score}%</span>
                    <span class="quiz-score-label">Your Score</span>
                </div>
                <div class="quiz-score-item">
                    <span class="quiz-score-value" style="color: var(--text-secondary); font-size: 24px;">${correct}/${total}</span>
                    <span class="quiz-score-label">Correct Answers</span>
                </div>
            </div>
            <button class="lesson-btn primary" id="retryQuizBtn" style="margin-top: 16px;">
                ${score >= 70 ? 'Continue' : 'Try Again'}
            </button>
            <button class="lesson-btn secondary" id="quizToModulesBtn" style="margin-top: 16px;">
                Back to Modules
            </button>
        </div>
    `;
    
    document.getElementById('retryQuizBtn').addEventListener('click', () => {
        startQuiz(AppState.training.currentQuiz);
    });
    
    document.getElementById('quizToModulesBtn').addEventListener('click', () => {
        navigateToView('modules');
    });
}

// Reports Functions
function generateReport(reportType) {
    const progress = calculateProgress();
    const reportData = {
        generatedAt: new Date().toLocaleString(),
        userID: AppState.user.id,
        sessionStarted: new Date(AppState.user.startedAt).toLocaleString(),
        modules: MODULES.map(module => {
            const state = AppState.training.modules[module.id];
            return {
                title: module.title,
                completed: state.completed,
                lessonsCompleted: state.lessonsCompleted,
                totalLessons: module.lessons.length,
                quizScore: state.quizScore,
                attempts: state.attempts
            };
        }),
        achievements: AppState.session.achievements.map(id => {
            const ach = ACHIEVEMENTS.find(a => a.id === id);
            return ach ? ach.name : id;
        }),
        totalXP: AppState.session.xpEarned,
        timeSpent: AppState.session.totalTimeSpent,
        progress: progress
    };
    
    let html = '';
    
    switch (reportType) {
        case 'summary':
            html = generateSummaryReport(reportData);
            break;
        case 'modules':
            html = generateModulesReport(reportData);
            break;
        case 'quiz':
            html = generateQuizReport(reportData);
            break;
        case 'full':
            html = generateFullReport(reportData);
            break;
    }
    
    downloadReport(html, `webxr-training-report-${reportType}-${Date.now()}.html`);
    showToast('success', 'Report Downloaded', `Your ${reportType} report is ready.`);
    
    // Add to recent reports
    addRecentReport(reportType);
}

function generateSummaryReport(data) {
    return `
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>WebXR Training - Progress Summary</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #0a0a12; color: #e8e8f0; padding: 40px; }
        .container { max-width: 800px; margin: 0 auto; }
        h1 { color: #00fff5; text-shadow: 0 0 20px rgba(0,255,245,0.3); }
        .stat-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 30px 0; }
        .stat-card { background: #1a1a2e; padding: 20px; border-radius: 12px; border: 1px solid rgba(0,255,245,0.2); }
        .stat-value { font-size: 32px; font-weight: bold; color: #00fff5; }
        .stat-label { color: #606070; margin-top: 5px; }
        .progress-bar { height: 10px; background: rgba(255,255,255,0.05); border-radius: 5px; margin: 10px 0; }
        .progress-fill { height: 100%; background: linear-gradient(90deg, #00fff5, #7b2cbf); border-radius: 5px; }
        .footer { margin-top: 40px; color: #606070; font-size: 12px; text-align: center; }
    </style>
</head>
<body>
    <div class="container">
        <h1>WebXR Training Progress Summary</h1>
        <p>Generated: ${data.generatedAt}</p>
        
        <div class="stat-grid">
            <div class="stat-card">
                <div class="stat-value">${data.progress.moduleProgress.toFixed(0)}%</div>
                <div class="stat-label">Overall Progress</div>
                <div class="progress-bar"><div class="progress-fill" style="width: ${data.progress.moduleProgress}%"></div></div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${data.totalXP}</div>
                <div class="stat-label">Total XP Earned</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${Math.floor(data.timeSpent / 60)}m</div>
                <div class="stat-label">Time Trained</div>
            </div>
        </div>
        
        <div class="stat-grid">
            <div class="stat-card">
                <div class="stat-value">${data.progress.completedModules}/${data.progress.totalModules}</div>
                <div class="stat-label">Modules Completed</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${data.progress.quizAccuracy.toFixed(0)}%</div>
                <div class="stat-label">Quiz Accuracy</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${data.achievements.length}</div>
                <div class="stat-label">Achievements</div>
            </div>
        </div>
        
        <div class="footer">
            WebXR Awareness Training Module | User ID: ${data.userID}
        </div>
    </div>
</body>
</html>
    `.trim();
}

function generateModulesReport(data) {
    let modulesHtml = data.modules.map(m => `
        <div style="background: #1a1a2e; padding: 15px; border-radius: 8px; margin: 10px 0; border-left: 3px solid ${m.completed ? '#00ff88' : '#606070'};">
            <strong style="color: #e8e8f0;">${m.title}</strong>
            <span style="color: ${m.completed ? '#00ff88' : '#606070'}; margin-left: 10px;">
                ${m.completed ? '✓ Completed' : 'Not Completed'}
            </span>
            <div style="margin-top: 8px; font-size: 13px; color: #a0a0b0;">
                Lessons: ${m.lessonsCompleted}/${m.totalLessons} | 
                Quiz: ${m.quizScore !== null ? m.quizScore + '%' : 'Not Taken'} | 
                Attempts: ${m.attempts}
            </div>
        </div>
    `).join('');
    
    return `
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>WebXR Training - Module Completion Report</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #0a0a12; color: #e8e8f0; padding: 40px; }
        .container { max-width: 800px; margin: 0 auto; }
        h1 { color: #00d4ff; text-shadow: 0 0 20px rgba(0,212,255,0.3); }
        table { width: 100%; border-collapse: collapse; margin: 30px 0; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.05); }
        th { color: #606070; font-weight: normal; }
        tr:hover { background: rgba(255,255,255,0.02); }
        .completed { color: #00ff88; }
        .footer { margin-top: 40px; color: #606070; font-size: 12px; text-align: center; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Module Completion Report</h1>
        <p>Generated: ${data.generatedAt} | User ID: ${data.userID}</p>
        
        <table>
            <thead>
                <tr>
                    <th>Module</th>
                    <th>Status</th>
                    <th>Lessons</th>
                    <th>Quiz Score</th>
                    <th>Attempts</th>
                </tr>
            </thead>
            <tbody>
                ${data.modules.map(m => `
                    <tr>
                        <td>${m.title}</td>
                        <td class="${m.completed ? 'completed' : ''}">${m.completed ? 'Completed' : 'Incomplete'}</td>
                        <td>${m.lessonsCompleted}/${m.totalLessons}</td>
                        <td>${m.quizScore !== null ? m.quizScore + '%' : '-'}</td>
                        <td>${m.attempts}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
        
        <div class="footer">
            WebXR Awareness Training Module
        </div>
    </div>
</body>
</html>
    `.trim();
}

function generateQuizReport(data) {
    let quizHtml = data.modules.filter(m => m.quizScore !== null).map(m => `
        <div style="background: #1a1a2e; padding: 15px; border-radius: 8px; margin: 10px 0; border-left: 3px solid ${m.quizScore >= 80 ? '#00ff88' : m.quizScore >= 60 ? '#ffd700' : '#ff00ff'};">
            <strong style="color: #e8e8f0;">${m.title}</strong>
            <span style="color: #a0a0b0; margin-left: 10px;">
                Score: ${m.quizScore}% | Attempts: ${m.attempts}
            </span>
        </div>
    `).join('');
    
    return `
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>WebXR Training - Quiz Performance Report</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #0a0a12; color: #e8e8f0; padding: 40px; }
        .container { max-width: 800px; margin: 0 auto; }
        h1 { color: #7b2cbf; text-shadow: 0 0 20px rgba(123,44,191,0.3); }
        .score-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; margin: 20px 0; }
        .score-card { background: #1a1a2e; padding: 15px; border-radius: 8px; text-align: center; }
        .score-value { font-size: 28px; font-weight: bold; color: #7b2cbf; }
        .score-label { color: #606070; font-size: 12px; }
        .footer { margin-top: 40px; color: #606070; font-size: 12px; text-align: center; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Quiz Performance Report</h1>
        <p>Generated: ${data.generatedAt} | User ID: ${data.userID}</p>
        
        <div class="score-grid">
            <div class="score-card">
                <div class="score-value">${data.progress.quizAccuracy.toFixed(0)}%</div>
                <div class="score-label">Average Score</div>
            </div>
            <div class="score-card">
                <div class="score-value">${data.modules.filter(m => m.quizScore !== null).length}</div>
                <div class="score-label">Quizzes Taken</div>
            </div>
        </div>
        
        <h3>Individual Quiz Results</h3>
        ${quizHtml}
        
        <div class="footer">
            WebXR Awareness Training Module
        </div>
    </div>
</body>
</html>
    `.trim();
}

function generateFullReport(data) {
    return `
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>WebXR Training - Full Report</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: linear-gradient(135deg, #0a0a12 0%, #1a1a2e 100%); color: #e8e8f0; padding: 40px; min-height: 100vh; }
        .container { max-width: 900px; margin: 0 auto; }
        h1 { color: #00fff5; text-shadow: 0 0 20px rgba(0,255,245,0.3); border-bottom: 1px solid rgba(0,255,245,0.2); padding-bottom: 10px; }
        h2 { color: #a0a0b0; font-size: 18px; margin: 30px 0 15px; }
        .report-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }
        .user-info { background: #1a1a2e; padding: 20px; border-radius: 12px; border: 1px solid rgba(0,255,245,0.2); }
        .info-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.05); }
        .info-label { color: #606070; }
        .info-value { color: #e8e8f0; font-weight: 500; }
        .stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 20px 0; }
        .stat-card { background: #1a1a2e; padding: 20px; border-radius: 12px; text-align: center; border: 1px solid rgba(0,255,245,0.1); }
        .stat-value { font-size: 28px; font-weight: bold; color: #00fff5; text-shadow: 0 0 10px rgba(0,255,245,0.3); }
        .stat-label { color: #606070; font-size: 12px; margin-top: 5px; }
        .modules-section { background: #1a1a2e; padding: 20px; border-radius: 12px; margin: 20px 0; }
        .module-item { display: flex; justify-content: space-between; align-items: center; padding: 12px; margin: 8px 0; background: rgba(255,255,255,0.02); border-radius: 8px; }
        .module-status { padding: 4px 12px; border-radius: 4px; font-size: 12px; font-weight: 600; }
        .status-completed { background: rgba(0,255,136,0.15); color: #00ff88; }
        .status-incomplete { background: rgba(255,255,255,0.05); color: #606070; }
        .achievements-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 15px 0; }
        .achievement-badge { background: #1a1a2e; padding: 15px; border-radius: 8px; text-align: center; border: 1px solid rgba(255,215,0,0.2); }
        .achievement-icon { font-size: 24px; color: #ffd700; }
        .achievement-name { color: #e8e8f0; margin-top: 5px; }
        .achievement-locked { opacity: 0.3; }
        .footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.05); color: #606070; font-size: 12px; text-align: center; }
        .progress-section { margin: 20px 0; }
        .progress-label { display: flex; justify-content: space-between; margin: 5px 0; font-size: 14px; }
        .progress-track { height: 8px; background: rgba(255,255,255,0.05); border-radius: 4px; overflow: hidden; }
        .progress-fill { height: 100%; background: linear-gradient(90deg, #00fff5, #7b2cbf); border-radius: 4px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="report-header">
            <h1>WebXR Training - Full Report</h1>
            <div style="color: #606070; font-size: 14px;">Generated: ${data.generatedAt}</div>
        </div>
        
        <div class="user-info">
            <div class="info-row">
                <span class="info-label">User ID</span>
                <span class="info-value">${data.userID}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Session Started</span>
                <span class="info-value">${data.sessionStarted}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Report Generated</span>
                <span class="info-value">${data.generatedAt}</span>
            </div>
        </div>
        
        <h2>Training Statistics</h2>
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">${data.progress.moduleProgress.toFixed(0)}%</div>
                <div class="stat-label">Progress</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${data.totalXP}</div>
                <div class="stat-label">Total XP</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${Math.floor(data.timeSpent / 60)}m</div>
                <div class="stat-label">Time Trained</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${data.achievements.length}</div>
                <div class="stat-label">Achievements</div>
            </div>
        </div>
        
        <h2>Module Progress</h2>
        <div class="modules-section">
            ${data.modules.map(m => `
                <div class="module-item">
                    <div>
                        <strong>${m.title}</strong>
                        <div style="font-size: 12px; color: #606070; margin-top: 3px;">
                            Lessons: ${m.lessonsCompleted}/${m.totalLessons} | Quiz: ${m.quizScore !== null ? m.quizScore + '%' : 'Not taken'} | Attempts: ${m.attempts}
                        </div>
                    </div>
                    <span class="module-status ${m.completed ? 'status-completed' : 'status-incomplete'}">
                        ${m.completed ? 'Completed' : 'In Progress'}
                    </span>
                </div>
            `).join('')}
        </div>
        
        <div class="progress-section">
            <div class="progress-label">
                <span>Modules Completed</span>
                <span>${data.progress.completedModules}/${data.progress.totalModules}</span>
            </div>
            <div class="progress-track"><div class="progress-fill" style="width: ${data.progress.moduleProgress}%"></div></div>
            
            <div class="progress-label" style="margin-top: 15px;">
                <span>Quiz Accuracy</span>
                <span>${data.progress.quizAccuracy.toFixed(0)}%</span>
            </div>
            <div class="progress-track"><div class="progress-fill" style="width: ${data.progress.quizAccuracy}%; background: linear-gradient(90deg, #7b2cbf, #ff00ff);"></div></div>
        </div>
        
        <h2>Achievements</h2>
        <div class="achievements-grid">
            ${ACHIEVEMENTS.map(ach => {
                const unlocked = data.achievements.includes(ach.id);
                return `
                    <div class="achievement-badge ${unlocked ? '' : 'achievement-locked'}">
                        <div class="achievement-icon">${unlocked ? ach.icon : '🔒'}</div>
                        <div class="achievement-name">${unlocked ? ach.name : 'Locked'}</div>
                    </div>
                `;
            }).join('')}
        </div>
        
        <div class="footer">
            WebXR Awareness Training Module<br>
            This report was automatically generated by the training system.
        </div>
    </div>
</body>
</html>
    `.trim();
}

function downloadReport(html, filename) {
    const blob = new Blob([html], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

function addRecentReport(type) {
    const list = document.getElementById('reportsList');
    const types = {
        summary: 'Progress Summary',
        modules: 'Module Completion',
        quiz: 'Quiz Performance',
        full: 'Full Training Report'
    };
    
    const item = document.createElement('div');
    item.className = 'recent-report-item';
    item.innerHTML = `
        <div class="recent-report-info">
            <div class="recent-report-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                    <polyline points="14 2 14 8 20 8"/>
                </svg>
            </div>
            <div>
                <div class="recent-report-name">${types[type]}</div>
                <div class="recent-report-date">${new Date().toLocaleString()}</div>
            </div>
        </div>
        <svg class="recent-report-download" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
        </svg>
    `;
    
    item.querySelector('.recent-report-download').addEventListener('click', () => {
        // Could regenerate and download the report
        generateReport(type);
    });
    
    list.insertBefore(item, list.firstChild);
    
    // Remove "no reports" message if present
    const noReports = list.querySelector('.no-reports');
    if (noReports) {
        noReports.remove();
    }
    
    // Limit to 5 recent reports
    while (list.children.length > 5) {
        list.removeChild(list.lastChild);
    }
}

// Toast Notifications
function showToast(type, title, message) {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const icons = {
        success: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>',
        info: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>',
        warning: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
        error: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>'
    };
    
    toast.innerHTML = `
        <div class="toast-icon">${icons[type]}</div>
        <div class="toast-content">
            <div class="toast-title">${title}</div>
            <div class="toast-message">${message}</div>
        </div>
    `;
    
    DOM.toastContainer.appendChild(toast);
    
    // Remove after animation
    setTimeout(() => {
        toast.remove();
    }, 3000);
}

// Reset Function
function resetProgress() {
    if (confirm('Are you sure you want to reset all progress? This cannot be undone.')) {
        localStorage.removeItem('webxr_training_state');
        
        // Reset state
        AppState.user = {
            id: generateUserId(),
            startedAt: Date.now(),
            completedModules: []
        };
        AppState.training = {
            currentModule: null,
            currentLesson: 0,
            modules: {},
            currentQuiz: null,
            quizAnswers: {},
            quizResults: []
        };
        AppState.session = {
            startTime: Date.now(),
            totalTimeSpent: 0,
            xpEarned: 0,
            achievements: []
        };
        
        initializeModuleState();
        saveState();
        updateProgressUI();
        renderAllModules();
        
        showToast('info', 'Progress Reset', 'Your training progress has been reset.');
        navigateToView('dashboard');
    }
}

// Event Listeners
function setupEventListeners() {
    // Navigation
    DOM.navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const view = item.dataset.view;
            navigateToView(view);
        });
    });
    
    // Reset button
    DOM.resetBtn.addEventListener('click', resetProgress);
    
    // Report buttons
    document.querySelectorAll('.report-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const type = btn.dataset.reportType;
            generateReport(type);
        });
    });
    
    // Lesson back button
    DOM.lessonBackBtn.addEventListener('click', () => {
        navigateToView('modules');
    });
    
    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            if (AppState.ui.currentView === 'lesson' || AppState.ui.currentView === 'quiz') {
                navigateToView('modules');
            }
        }
    });
}

// Session Time Tracking
function trackSessionTime() {
    const lastTime = AppState.session.startTime;
    const now = Date.now();
    const elapsed = (now - lastTime) / 60000; // Convert to minutes
    
    AppState.session.totalTimeSpent += Math.min(elapsed, 5); // Cap at 5 min per tick
    AppState.session.startTime = now;
}

// Initialize Application
function init() {
    console.log('=== init() called ===');
    console.log('Document readyState:', document.readyState);
    
    // Critical check - ensure DOM elements exist
    const dashboardView = document.getElementById('dashboardView');
    const modulesGrid = document.getElementById('allModulesGrid');
    
    if (!dashboardView || !modulesGrid) {
        console.error('CRITICAL: Required DOM elements not found!');
        console.error('dashboardView:', dashboardView);
        console.error('modulesGrid:', modulesGrid);
        document.body.innerHTML += '<div style="background:red;color:white;padding:20px;">ERROR: Required DOM elements not found. Make sure app.js is loaded correctly.</div>';
        return;
    }
    
    console.log('Dashboard view exists:', !!dashboardView);
    console.log('Modules grid exists:', !!modulesGrid);
    
    loadState();
    initializeModuleState();
    
    console.log('User ID:', AppState.user.id);
    console.log('Modules in state:', Object.keys(AppState.training.modules).length);
    
    console.log('Setting up event listeners...');
    setupEventListeners();
    console.log('Updating progress UI...');
    updateProgressUI();
    console.log('Rendering all modules...');
    const result = renderAllModules();
    console.log('renderAllModules returned:', result);
    
    console.log('=== init() completed ===');
    
    // Start time tracking
    setInterval(trackSessionTime, 60000); // Track every minute
    
    // Navigate to dashboard
    navigateToView('dashboard');
}

// Start the application - call immediately with fallback
(function startApp() {
    console.log('startApp() called, readyState:', document.readyState);
    
    if (document.readyState === 'loading') {
        console.log('Waiting for DOMContentLoaded...');
        document.addEventListener('DOMContentLoaded', init);
    } else {
        console.log('DOM already ready, calling init()...');
        init();
    }
    
    // Safety: Always call init after a short delay if not already done
    setTimeout(() => {
        const dashboardView = document.getElementById('dashboardView');
        if (dashboardView && !dashboardView.classList.contains('active')) {
            console.log('Safety init triggered...');
            init();
        }
    }, 200);
})();
