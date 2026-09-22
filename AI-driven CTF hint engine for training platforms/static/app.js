(function () {
  "use strict";

  var clock = document.getElementById("clock");
  if (clock) {
    function tick() {
      clock.textContent = new Date().toLocaleString();
    }
    tick();
    setInterval(tick, 1000);
  }

  window.app = {
    post: async function (url, body) {
      var res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body || {})
      });
      if (!res.ok) {
        var data = null;
        try { data = await res.json(); } catch (e) { /* ignore */ }
        throw new Error((data && data.error) || ("HTTP " + res.status));
      }
      return res.json();
    }
  };
})();