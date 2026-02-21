# 🧩 UI Components & Interaction

## 1. Buttons (Engineering Style)
Buttons should feel solid and precise, with clear state changes.

*   **Primary CTA (Call to Action):**
    *   *Default:* Background `Green-500 (#00D084)`, Text `Navy-900`, `4px` border-radius.
    *   *Hover:* Background `Green-600 (#00A86B)`, Button elevates slightly (Shadow `sm`).
    *   *Active (Click):* Background `Green-600`, shadow removed, scaled down to `0.98`.
    *   *Disabled:* Background `Gray-100`, Text `Gray-500`, cursor `not-allowed`.
*   **Secondary Button:**
    *   *Default:* Transparent background, Border `2px solid Navy-900`, Text `Navy-900`.
    *   *Hover:* Background `Navy-900`, Text `White`.

## 2. Forms & Inputs
Inputs should provide instant validation feedback to ensure high lead quality.

*   **Default Input Field:**
    *   Border `1px solid Gray-500`, Background `White`, `4px` radius.
*   **Focus State:**
    *   Border `2px solid Green-500`, Box-shadow `0 0 0 3px rgba(0, 208, 132, 0.2)`.
*   **Error State:**
    *   Border `2px solid Red-500`, Error message below input in `14px Red-500`.

## 3. Project Cards (Referenzen)
Used to showcase completed solar installations.

*   **Structure:** Image top, Content bottom.
*   **Hover Effect:** 
    *   Image darkens slightly (`rgba(0,0,0,0.2)` overlay).
    *   Technical data slides up smoothly (e.g., "Yield: 500 kWp | Build time: 3 weeks").
*   **Shadow:** Default `sm` shadow, on hover expands to `lg` shadow to indicate clickability.

## 4. Multi-step Lead Form (Quiz)
The conversion engine of the site.
*   **Progress Bar:** Sticky top, `Green-500` fill indicating percentage completed.
*   **Selection Cards (Radio Alternatives):** Large clickable cards (e.g., "House", "Factory") with SVG icons.
    *   *Selected State:* Border `2px solid Green-500`, subtle `Green-100` background.
