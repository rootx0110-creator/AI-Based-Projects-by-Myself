============================================================
 ORBIT — 3D PRODUCT CONFIGURATOR
 Drag · Rotate · Zoom · Customize · HTML Report
============================================================

WHAT IS THIS?
-------------
A desktop app that shows a 3D product you can turn, zoom and
customize in real time. Pick one of four reference products
(lounge chair, floor lamp, coffee table, bookshelf), change the
finish of any part, add/remove options, watch the price update
live — then download a professional HTML report of your
configuration.

QUICK START
-----------
1. Double-click:  3D-Product-Configurator.exe
2. A window opens with the 3D product. That's it.

(First launch takes a few seconds while the app unpacks itself.)

CONTROLS
--------
  Left-drag ......... rotate the product
  Mouse wheel ....... zoom in / out
  Right-drag ........ pan the view (or hold Shift + drag)
  Click a part ...... select it for customization
  Buttons (bottom) .. reset view / auto-rotate / fullscreen

CUSTOMIZING
-----------
  * Pick a product: Lounge Chair / Floor Lamp / Coffee Table /
    Bookshelf (chips at the top of the side panel)
  * Pick a part (chips below, or click it on the model)
  * Choose one of 12 finishes — each part keeps its own finish
  * Options per product, e.g. chair: cushion pad (+$25),
    armrests (+$20), metal legs (+$35), lamp: dimmer (+$15),
    warm LED bulb (+$12), table: drawer (+$45), glass top (+$60),
    shelf: extra shelf (+$18), glass doors (+$55) — plus
    engraving (+$5, max 12 characters) on every product
  * Try the per-product presets — or roll the dice
  * Each product keeps its own configuration, remembered for
    next time

REPORTS & EXPORTS
-----------------
  [Download report (.html)]  saves a styled quotation document with
                             all finishes, options and the final price
  [PNG]                      saves a snapshot of the current view
  [Copy]                     copies your configuration as JSON

TROUBLESHOOTING
---------------
  * Nothing happens / no window?
    - The app needs Chrome or Edge installed (any recent version).
    - Check your antivirus didn't quarantine the exe.
    - If a window did not open, look in the console window for a line
      like:  Local server: http://127.0.0.1:8642
      You can open that address in any browser.
  * SmartScreen warning on first run?
    The exe is unsigned; choose "More info" -> "Run anyway".
  * Want a full reset?
    Delete the folder  %LOCALAPPDATA%\Orbit3D  and run the exe again.
  * Headless check (no window):
    run  3D-Product-Configurator.exe --selftest  in a terminal.

REBUILDING FROM SOURCE (optional)
---------------------------------
  Requirements: Windows, Node.js, .NET Framework 4.x (built-in),
                Chrome or Edge.
  Commands:
     node tools/fetch-node.js   (one-time runtime download)
     npm run build              (creates 3D-Product-Configurator.exe)

PRIVACY
-------
Everything runs locally. The server only listens on 127.0.0.1 and no
data ever leaves your machine.

------------------------------------------------------------
 ORBIT v1.0.0 · ORBIT Labs · MIT license
============================================================
