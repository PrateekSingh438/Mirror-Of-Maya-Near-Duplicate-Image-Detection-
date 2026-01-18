# Animation System Documentation

## Overview

The Mirror of Maya frontend features an elegant animation system designed to provide visual feedback during model execution and enhance user engagement throughout the interface.

---

## Chakra Animation Suite

All animations are defined in `tailwind.config.js` under `theme.extend.animation` and triggered during specific application states.

### 1. spin-chakra (Primary Rotation)

**Duration**: 10 seconds  
**Effect**: Full 360° rotation  
**Usage**: Center icon during model scanning  
**CSS**:
```css
@keyframes spin-chakra {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
```

**HTML**:
```jsx
<Zap className="animate-spin-chakra" size={24} />
```

**When Used**:
- Dashboard empty state (center)
- QueryTool searching state
- Model is processing data

---

### 2. pulse-chakra (Outer Ring Pulse)

**Duration**: 2.5 seconds  
**Effect**: Scales from 1.0 → 1.15, opacity 0.5 → 0.8  
**Usage**: Outer ring of chakra indicator  
**CSS**:
```css
@keyframes pulse-chakra {
  0%, 100% { 
    transform: scale(1); 
    opacity: 0.5;
  }
  50% { 
    transform: scale(1.15); 
    opacity: 0.8;
  }
}
```

**HTML**:
```jsx
<div className="border-4 border-saffron-400 rounded-full h-32 w-32 animate-pulse-chakra"></div>
```

**When Used**:
- Dashboard empty state (outer ring)
- Loading indicators
- Active processing visualization

---

### 3. pulse-inner (Inner Ring Counter-Pulse)

**Duration**: 3 seconds  
**Effect**: Inverse pulse (scales down while outer scales up)  
**Usage**: Inner ring, creates layered pulse effect  
**CSS**:
```css
@keyframes pulse-inner {
  0%, 100% { 
    transform: scale(1); 
    opacity: 0.8;
  }
  50% { 
    transform: scale(0.85); 
    opacity: 0.5;
  }
}
```

**HTML**:
```jsx
<div className="border-2 border-gold rounded-full h-24 w-24 animate-pulse-inner"></div>
```

**Combined Effect** (with pulse-chakra):
```jsx
<div className="relative w-32 h-32 flex items-center justify-center">
  {/* Outer ring pulsing out */}
  <div className="absolute border-4 border-saffron-400 rounded-full w-32 h-32 animate-pulse-chakra"></div>
  
  {/* Inner ring pulsing in (inverse timing) */}
  <div className="absolute border-2 border-gold rounded-full w-24 h-24 animate-pulse-inner"></div>
  
  {/* Center spinning icon */}
  <Zap className="animate-spin-chakra relative z-10" />
</div>
```

---

### 4. float (Vertical Floating Motion)

**Duration**: 3 seconds  
**Effect**: Moves up and down by ±10px  
**Usage**: Creates hovering effect  
**CSS**:
```css
@keyframes float {
  0%, 100% { 
    transform: translateY(0px); 
  }
  50% { 
    transform: translateY(-10px); 
  }
}
```

**HTML**:
```jsx
<ImageIcon size={64} className="text-indigo-400 animate-float" />
```

**When Used**:
- Empty state icons
- Loading placeholders
- Attention-drawing elements

---

### 5. glow (Shadow Pulse)

**Duration**: 2 seconds  
**Effect**: Box-shadow intensity pulse  
**Usage**: Creates glowing halo effect  
**CSS**:
```css
@keyframes glow {
  0%, 100% { 
    box-shadow: 0 0 10px rgba(255, 159, 28, 0.3), 
                0 0 20px rgba(255, 159, 28, 0.1);
  }
  50% { 
    box-shadow: 0 0 20px rgba(255, 159, 28, 0.6), 
                0 0 40px rgba(255, 159, 28, 0.3);
  }
}
```

**HTML**:
```jsx
<div className="rounded-lg p-6 bg-indigo-900 animate-glow">
  Content with glowing halo
</div>
```

**When Used**:
- Card hover states
- Active elements
- Emphasis on important sections

---

### 6. shimmer (Shine Effect)

**Duration**: 2 seconds  
**Effect**: Light reflection across surface  
**Usage**: Skeleton loader or loading placeholder  
**CSS**:
```css
@keyframes shimmer {
  0% { 
    background-position: -1000px 0;
  }
  100% { 
    background-position: 1000px 0;
  }
}
```

**HTML**:
```jsx
<div className="h-12 rounded-lg bg-gradient-to-r from-transparent via-white/20 to-transparent animate-shimmer"></div>
```

**When Used**:
- Skeleton loading states
- Placeholder cards
- Data loading feedback

---

## Animation States in Components

### Dashboard Component

```jsx
// EMPTY STATE - No data loaded yet
{!metrics && (
  <div className="flex flex-col items-center justify-center py-20">
    <div className="animate-float">                          {/* Floating motion */}
      <div className="animate-pulse-chakra 
                      border-4 border-saffron-400"></div>    {/* Outer pulse */}
      <div className="animate-pulse-inner 
                      border-2 border-gold"></div>           {/* Inner pulse */}
      <Zap className="animate-spin-chakra" />              {/* Center spin */}
    </div>
    <p className="text-parchment-300">Scanning dataset...</p>
  </div>
)}

// LOADED STATE - Data available
{metrics && (
  <div className="grid grid-cols-4 gap-4">
    {/* Metric cards with hover animation */}
    {metrics.map(metric => (
      <div key={metric.id} 
           className="card group 
                      hover:-translate-y-1 
                      hover:shadow-saffron-glow 
                      transition-all duration-300">
        {/* Card content */}
      </div>
    ))}
  </div>
)}
```

### QueryTool Component

```jsx
{/* SEARCHING STATE */}
{isSearching && (
  <button disabled className="btn-primary opacity-75">
    <div className="animate-spin rounded-full h-5 w-5 
                    border-2 border-maya-darker 
                    border-t-parchment-300"></div>
    Searching...
  </button>
)}

{/* RESULTS STATE */}
{results.length > 0 && (
  <div className="results-grid">
    {results.map(result => (
      <div className="card group 
                      hover:shadow-lg 
                      hover:shadow-saffron-400/20 
                      hover:-translate-y-1 
                      transition-all">
        {/* Result card with hover lift */}
      </div>
    ))}
  </div>
)}

{/* NO RESULTS STATE */}
{results.length === 0 && selectedFile && !isSearching && (
  <div className="flex flex-col items-center py-12">
    <ImageIcon className="text-indigo-400 
                         animate-float 
                         mb-4" />
    <p className="text-parchment-300">
      No duplicates found
    </p>
  </div>
)}
```

### ClustersView Component

```jsx
{/* LOADING STATE */}
{isLoading && (
  <div className="flex flex-col items-center py-20">
    <div className="animate-spin rounded-full 
                    h-12 w-12 
                    border-4 border-saffron-400 
                    border-t-gold"></div>
    <p className="text-parchment-300">Loading clusters...</p>
  </div>
)}

{/* IMAGE SELECTION */}
{isSelected && (
  <div className="absolute inset-0 
                  bg-saffron-400/20 
                  flex items-center justify-center">
    <div className="text-4xl font-bold 
                    text-saffron-300 
                    animate-bounce">
      ✓
    </div>
  </div>
)}

{/* DELETE BANNER */}
{selectedFiles.size > 0 && (
  <div className="mb-6 p-4 
                  bg-red-600/20 
                  border border-red-400 
                  rounded-lg 
                  animate-pulse">
    {selectedFiles.size} forms marked for deletion
  </div>
)}
```

---

## Animation Timing Reference

| Animation | Duration | Curve | Use Case |
|-----------|----------|-------|----------|
| spin-chakra | 10s | linear | Center rotation |
| pulse-chakra | 2.5s | ease-in-out | Outer ring pulse |
| pulse-inner | 3s | ease-in-out | Inner ring (inverse) |
| float | 3s | ease-in-out | Floating motion |
| glow | 2s | ease-in-out | Shadow pulse |
| shimmer | 2s | linear | Shine effect |
| bounce | 1s | cubic-bezier | Selection checkmarks |
| pulse | 2s | cubic-bezier | Standard Tailwind pulse |
| spin | 1s | linear | Loading spinners |

---

## Layering Animations

Multiple animations can be combined on the same element:

```jsx
{/* Element with multiple animations */}
<div className="animate-float 
                animate-pulse-chakra 
                animate-spin-chakra 
                border-4 border-saffron-400">
  Content
</div>

{/* This applies all three animations simultaneously:
    1. Vertical floating motion (animate-float)
    2. Pulsing scale effect (animate-pulse-chakra)
    3. 360° rotation (animate-spin-chakra)
*/}
```

---

## Performance Optimization

### GPU Acceleration

All animations use CSS transforms for GPU acceleration:
```css
/* Good - GPU accelerated */
transform: translate(), scale(), rotate()

/* Avoid - CPU rendered */
left, top, width, height, margin, padding
```

### Reduced Motion

Support users with accessibility needs:
```css
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

### Animation Timing

Stagger animations for visual interest:
```jsx
{/* Staggered animation delays */}
{items.map((item, index) => (
  <div key={index} 
       style={{ animationDelay: `${index * 100}ms` }}
       className="animate-fadeIn">
    {item}
  </div>
))}
```

---

## Browser Compatibility

All animations use standard CSS3 with:
- ✅ Chrome 88+
- ✅ Firefox 85+
- ✅ Safari 14+
- ✅ Edge 88+
- ✅ Mobile browsers (iOS 14+, Android 9+)

---

## Customizing Animations

To modify animation in `tailwind.config.js`:

```javascript
module.exports = {
  theme: {
    extend: {
      animation: {
        'spin-chakra': 'spin-chakra 10s linear infinite',
        'pulse-chakra': 'pulse-chakra 2.5s ease-in-out infinite',
        'pulse-inner': 'pulse-inner 3s ease-in-out infinite',
      },
      keyframes: {
        'spin-chakra': {
          '0%': { transform: 'rotate(0deg)' },
          '100%': { transform: 'rotate(360deg)' },
        },
        'pulse-chakra': {
          '0%, 100%': { transform: 'scale(1)', opacity: '0.5' },
          '50%': { transform: 'scale(1.15)', opacity: '0.8' },
        },
        // ... more keyframes
      }
    }
  }
}
```

---

## Animation Patterns Used

### Pattern 1: Loading Spinner
```jsx
<div className="animate-spin rounded-full h-12 w-12 
                border-4 border-gray-300 
                border-t-blue-500"></div>
```

### Pattern 2: Floating Icon
```jsx
<Icon className="animate-float text-indigo-400" />
```

### Pattern 3: Pulsing Badge
```jsx
<span className="inline-flex items-center 
                 px-3 py-1 rounded-full 
                 bg-blue-500/20 
                 animate-pulse">
  Live
</span>
```

### Pattern 4: Hover Lift
```jsx
<div className="card 
               hover:-translate-y-1 
               hover:shadow-lg 
               transition-all duration-300">
  Content
</div>
```

### Pattern 5: Multi-Layer Animation
```jsx
<div className="relative h-32 w-32">
  <div className="absolute inset-0 
                  rounded-full 
                  border-4 border-saffron-400 
                  animate-pulse-chakra"></div>
  <div className="absolute inset-2 
                  rounded-full 
                  border-2 border-gold 
                  animate-pulse-inner"></div>
  <Icon className="absolute inset-10 
                   animate-spin-chakra" />
</div>
```

---

## Testing Animations

### Visual Testing
1. Run `npm run dev`
2. Navigate to Dashboard
3. Trigger model scan to see animations
4. Check QueryTool for upload animations
5. Resize window to test responsive animations

### Performance Testing
1. Open Chrome DevTools → Performance tab
2. Record while animations running
3. Check for janky frames (should be smooth 60fps)
4. Look for GPU acceleration in layers

### Accessibility Testing
1. Enable "Reduce motion" in OS settings
2. Verify animations pause/reduce
3. Test keyboard navigation
4. Check screen reader compatibility

---

## Future Enhancement Ideas

1. **Page Transitions** - Add fade/slide animations between tabs
2. **Skeleton Loaders** - Shimmer placeholders while loading
3. **Gesture Animations** - Swipe/pinch animations on mobile
4. **Particle Effects** - Floating particles in background
5. **Wave Effects** - Water-like animations for data flow
6. **3D Transforms** - Perspective and rotation effects

---

**Animation System Status**: ✅ Complete and Production Ready
