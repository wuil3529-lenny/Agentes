# Animation Recipes (Emil Kowalski Craft)

## 1. Button Press
```css
.btn-press {
  transition: transform 120ms cubic-bezier(0.23, 1, 0.32, 1);
}
@media (hover: hover) and (pointer: fine) {
  .btn-press:hover { transform: translateY(-1px); }
}
.btn-press:active { transform: scale(0.97); }
```

## 2. Dropdown / Popover
```css
.popover-menu {
  transform-origin: var(--transform-origin, top center);
  transition: transform 180ms cubic-bezier(0.23, 1, 0.32, 1),
              opacity 180ms cubic-bezier(0.23, 1, 0.32, 1);
}
.popover-menu[data-state="closed"] {
  transform: scale(0.95);
  opacity: 0;
}
.popover-menu[data-state="open"] {
  transform: scale(1);
  opacity: 1;
}
```

## 3. Modal / Dialog
```css
.modal-overlay {
  transition: opacity 220ms cubic-bezier(0.23, 1, 0.32, 1);
}
.modal-content {
  transform: translate(-50%, -50%) scale(1);
  transition: transform 220ms cubic-bezier(0.23, 1, 0.32, 1),
              opacity 220ms cubic-bezier(0.23, 1, 0.32, 1);
}
.modal-content[data-state="closed"] {
  transform: translate(-50%, -48%) scale(0.96);
  opacity: 0;
}
```

## 4. Staggered Dashboard Cards (React / Motion)
```jsx
const containerVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.045 } },
};
const cardVariants = {
  hidden: { opacity: 0, transform: "translateY(12px) scale(0.98)" },
  visible: { opacity: 1, transform: "translateY(0) scale(1)", transition: { duration: 0.28, ease: [0.23, 1, 0.32, 1] } },
};
```

## 5. Sliding Tab Indicator (React / Motion)
```jsx
{isActive && (
  <motion.div
    layoutId="activeTab"
    className="absolute inset-0 bg-white rounded-full shadow-sm"
    transition={{ type: "spring", duration: 0.38, bounce: 0.15 }}
  />
)}
```
