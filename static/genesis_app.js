// genesis_app.js — обогащение сообщений контекстом
// Погода, курсы, новости, космос, YouTube, Wikipedia, Fandom
// Контекст уходит ОТДЕЛЬНЫМ полем в /api/chat. Пузырь пользователя чистый.
// Маркер источника (wikipedia · weather) дописывается под ответом KAIROS.
(function () {
  "use strict";

  async function enhanceMessageWithContext(text) {
    var t = text.toLowerCase();
    var blocks = [];
    var sources = [];

    // 1. YouTube — поиск видео
    var ytMatch = t.match(/(?:найди|покажи|поищи)\s+(?:видео|ролик[и]?|клип[ы]?)\s+(?:про|о|по)?\s*(.+)$/i)
              || t.match(/(?:видео|ролик[и]?|клип[ы]?)\s+(?:про|о|по)\s+(.+)$/i)
              || t.match(/^youtube[:\s]+(.+)$/i)
              || t.match(/^ютуб[:\s]+(.+)$/i);
    if (ytMatch && ytMatch[1]) {
      var ytQ = ytMatch[1].trim().replace(/[?!.,]+$/, "");
      if (ytQ.length >= 2) {
        try {
          var ryt = await fetch("/api/youtube?q=" + encodeURIComponent(ytQ));
          var dyt = await ryt.json();
          if (dyt.ok && dyt.items && dyt.items.length) {
            var ytLines = dyt.items.map(function (v) {
              return "• " + v.title + " — " + v.url;
            }).join("\n");
            blocks.push("[YOUTUBE: найдены видео по запросу \"" + ytQ + "\":\n" + ytLines + "]");
            sources.push("youtube");
          }
        } catch (e) { console.warn("[CTX] youtube", e); }
      }
    }

    // 2. Погода
    if (/погод|weather|температур|дожд|солнечн|ветер|облачн/.test(t)) {
      try {
        var rw = await fetch("/api/weather");
        var dw = await rw.json();
        if (dw.ok) {
          blocks.push("[ПОГОДА: " + dw.city + ", " + dw.temp + "°C, " + dw.desc +
            ", влажность " + dw.humidity + "%, ощущается как " + dw.feels + "°C]");
          sources.push("weather");
        }
      } catch (e) { console.warn("[CTX] weather", e); }
    }

    // 3. Курсы
    if (/курс|доллар|евро|злот|валют|usd|eur|pln|byn/.test(t)) {
      try {
        var rc = await fetch("/api/currencies");
        var dc = await rc.json();
        if (dc.ok) {
          blocks.push("[КУРСЫ НБРБ: USD=" + dc.USD.toFixed(3) + ", EUR=" + dc.EUR.toFixed(3) +
            ", PLN=" + dc.PLN.toFixed(3) + ", BYN=1.00]");
          sources.push("currencies");
        }
      } catch (e) { console.warn("[CTX] cur", e); }
    }

    // 4. Новости
    if (/новост|news|что нового|заголовк/.test(t)) {
      try {
        var rn = await fetch("/api/news");
        var dn = await rn.json();
        if (dn.ok && dn.news && dn.news.length) {
          var titles = dn.news.slice(0, 5).map(function (n) { return "• " + n.title; }).join("; ");
          blocks.push("[СВЕЖИЕ НОВОСТИ: " + titles + "]");
          sources.push("news");
        }
      } catch (e) { console.warn("[CTX] news", e); }
    }

    // 5. Космос
    if (/космос|луна|лунн|space|фаза луны|астро/.test(t)) {
      try {
        var rs = await fetch("/api/space");
        var ds = await rs.json();
        if (ds.ok) {
          blocks.push("[КОСМОС: " + ds.moon_name + " " + ds.moon_emoji +
            ". Факт: " + ds.fact + "]");
          sources.push("space");
        }
      } catch (e) { console.warn("[CTX] space", e); }
    }

    // 6. Wikipedia / Fandom
    var wikiMatch = t.match(/(?:расскажи\s+про|расскажи\s+о|кто\s+так(?:ой|ая|ое|ие)|что\s+такое|информация\s+о|найди\s+про)\s+(.+)$/i);
    if (wikiMatch) {
      var q = wikiMatch[1].trim().replace(/[?!.,]+$/, "");
      if (q.length >= 2) {
        try {
          var rwk = await fetch("/api/wiki?q=" + encodeURIComponent(q));
          var dwk = await rwk.json();
          if (dwk.ok && dwk.extract) {
            blocks.push("[WIKIPEDIA: " + dwk.title + " — " + dwk.extract + "]");
            if (dwk.url) window.__lastCtxUrl = dwk.url;
            sources.push("wikipedia");
          } else {
            try {
              var rfd = await fetch("/api/fandom?q=" + encodeURIComponent(q));
              var dfd = await rfd.json();
              if (dfd.ok && dfd.extract) {
                blocks.push("[FANDOM: " + dfd.title + " — " + dfd.extract + "]");
                if (dfd.url) window.__lastCtxUrl = dfd.url;
                sources.push("fandom");
              }
            } catch (e) { console.warn("[CTX] fandom", e); }
          }
        } catch (e) { console.warn("[CTX] wiki", e); }
      }
    }

    if (!blocks.length) return { text: text, context: "", sources: [] };
    return { text: text, context: blocks.join("\n"), sources: sources };
  }

  // Fetch-монитор — перехватывает POST /api/chat, добавляет context
  window.addEventListener("load", function () {
    if (window.__ctxMonitorInstalled) return;
    window.__ctxMonitorInstalled = true;

    var origFetch = window.fetch.bind(window);

    window.fetch = async function (input, init) {
      var url = (typeof input === "string") ? input : (input && input.url) || "";
      var isChat = (url === "/api/chat" || url.indexOf("/api/chat") === 0);

      if (isChat && init && init.method === "POST" && init.body) {
        try {
          var body = JSON.parse(init.body);
          if (body && body.text && !body.context) {
            var r = await enhanceMessageWithContext(body.text);
            window.__lastCtxSources = r.sources || [];
            if (r.context) {
              body.context = r.context;
              init = Object.assign({}, init, { body: JSON.stringify(body) });
              console.log("[CTX] context добавлен:", r.context.length, "симв. Источники:", r.sources.join(", "));
            } else {
              console.log("[CTX] контекст пуст (источники не сработали).");
            }
          }
        } catch (e) {
          console.warn("[CTX] body parse", e);
        }
      }

      return origFetch(input, init);
    };

    // Обёртка addKairosMessage — маркер + ссылка
    var origAdd = window.addKairosMessage;
    if (typeof origAdd !== "function") {
      console.warn("[CTX] addKairosMessage не найден");
    } else {
      window.addKairosMessage = function (text) {
        origAdd.call(this, text);
        var srcs = window.__lastCtxSources || [];
        window.__lastCtxSources = null;
        if (!srcs.length) return;
        var msgs = document.querySelectorAll(".chat-msg.kairos .msg-text");
        var last = msgs[msgs.length - 1];
        if (!last) return;

        // Маркер
        var small = document.createElement("small");
        small.className = "ctx-sources";
        small.textContent = srcs.join(" \u00b7 ");
        last.appendChild(small);

        // Ссылка (если есть URL)
        var pageUrl = window.__lastCtxUrl;
        if (pageUrl) {
          var link = document.createElement("a");
          link.className = "ctx-link";
          link.href = pageUrl;
          link.target = "_blank";
          link.rel = "noopener";
          link.textContent = (srcs[0] === "fandom" ? "fandom" : "wikipedia") + " \u2192";
          last.appendChild(link);
          window.__lastCtxUrl = null;
        }
      };
      console.log("[CTX] обёртка addKairosMessage установлена.");
    }

    console.log("[CTX] fetch-монитор установлен.");
  });
})();
