// Build Saver (formerly Skill Saver) - in-game panel v4.0 (needs the SDK mod SkillSaver.sdkmod v4.0)
// Runs inside the game's UI engine (Coherent Gameface), loaded by menu_bigmap.html into the status
// menu document (coui://uiresources/ingame.html?view=view_status_menus). Talks to the mod over
// 127.0.0.1:19417. It only adds its own elements; nothing of the game's menus is changed.
// v1.3: four styles (STYLE button in the panel cycles them, the choice is remembered):
//         native - like the skill page itself (class box with cyan bar, grey title, Industry fonts)
//         tree   - takes the colour of the open skill tree (red / green / blue), node-like buttons
//         echo   - ECHO / tooltip look: cyan frame, uppercase, orange hover like the game's lists
//         classic- Borderlands yellow / black
//       Fonts and colours come from the game's own skill page (style dump of v1.2).
(function (global) {
    "use strict";
    if (global.__SkillSaverUI_v1) return;
    global.__SkillSaverUI_v1 = true;

    var BASE = "http://127.0.0.1:19417/skillsaver-ui-v1";
    var HOST_TAG = "widget-skills";
    var DEFAULT_THEME = "native";
    var CHAR = { corpohacker: "Loveless", darksiren: "Vex", exosoldier: "Rafa", gravitar: "Harlowe",
                 paladin: "Amon", robodealer: "C4SH" };
    var TREE = { red: "#ff5b3a", green: "#3fd77f", blue: "#1abaff", purple: "#b06cff", yellow: "#ffc94a", orange: "#ff9a2e" };

    // fonts of the skill page (fallbacks only matter outside the game)
    var FB = ', "DejaVu Sans Condensed", "Arial Narrow", sans-serif';
    var F = { demi: '"Industry-DemiBold"' + FB, med: '"Industry-Medium"' + FB, norm: '"Industry-Normal"' + FB,
              num: '"Mononum-Industry-Medium"' + FB };
    var CYAN = "#1abaff", GREY = "rgb(159,173,176)", STEEL = "rgb(63,118,157)", ORANGE = "#f5a623";
    var OK = "#55e08a", BAD = "#ff5f4a", WARN = "#ffc94a";

    function rgba(hex, a) {
        var h = hex.replace("#", "");
        return "rgba(" + parseInt(h.substr(0, 2), 16) + "," + parseInt(h.substr(2, 2), 16) + "," + parseInt(h.substr(4, 2), 16) + "," + a + ")";
    }

    // ------------------------------------------------------------ styles
    // every theme returns css strings; "acc" is the colour of the open skill tree
    var THEMES = {
        native: {
            label: "Native",
            text: "#c9d3d6", dim: "#5f7987", warn: WARN,
            panel: function () { return "background-color:rgba(3,16,26,.9);border-left:.3rem solid " + CYAN + ";padding:2rem 2.2rem;"; },
            title: "font-family:" + F.demi + ";font-size:3.6rem;color:" + GREY + ";",
            sub: "font-family:" + F.med + ";font-size:2rem;color:" + CYAN + ";",
            btn: function () { return "font-family:" + F.med + ";font-size:1.9rem;color:" + CYAN + ";background-color:rgba(3,16,26,.85);border-left:.2rem solid " + CYAN + ";padding:.5rem 1.2rem .6rem;"; },
            btnHover: function () { return "background-color:" + rgba("#1abaff", .2) + ";color:#ffffff;"; },
            row: function () { return "background-color:rgba(10,30,44,.75);border-left:.2rem solid " + STEEL + ";padding:.8rem 1.2rem;"; },
            rowHover: function () { return "border-left-color:" + CYAN + ";"; },
            rowSel: function () { return "background-color:" + rgba("#1abaff", .16) + ";border-left:.3rem solid " + CYAN + ";"; },
            name: "font-family:" + F.med + ";font-size:2.2rem;color:#dfe7ea;",
            meta: "font-family:" + F.norm + ";font-size:1.6rem;color:" + STEEL + ";",
            pts: "font-family:" + F.num + ";font-size:2.2rem;color:" + GREY + ";",
            secLabel: function () { return "font-family:" + F.med + ";font-size:1.6rem;letter-spacing:.15rem;color:" + STEEL + ";"; },
            secLine: function () { return "background-color:" + rgba("#3f769d", .45) + ";"; },
            key: "font-family:" + F.med + ";font-size:1.8rem;color:" + STEEL + ";",
            val: "font-family:" + F.med + ";font-size:1.9rem;color:#c9d3d6;",
            launcher: function () { return "font-family:" + F.med + ";font-size:2.8rem;color:" + CYAN + ";background-color:rgba(3,16,26,.8);border-left:.3rem solid " + CYAN + ";padding:.4rem 1.6rem .6rem;"; },
            launcherHover: function () { return "background-color:" + rgba("#1abaff", .2) + ";color:#ffffff;"; },
            upper: false
        },
        tree: {
            label: "Tree colour",
            text: "#e2e6e8", dim: "#7d8790", warn: WARN,
            panel: function (a) { return "background-color:rgba(6,9,13,.93);background-image:linear-gradient(to top," + rgba(a, .28) + ",rgba(6,9,13,0) 55%);border:1px solid " + rgba(a, .6) + ";padding:2rem 2.2rem;"; },
            deco: function (p, a) { corners(p, a, "2.2rem", ".3rem"); },
            title: "font-family:" + F.demi + ";font-size:3.6rem;color:#e9eef0;",
            sub: "font-family:" + F.med + ";font-size:2rem;color:" + GREY + ";",
            btn: function (a) { return "font-family:" + F.demi + ";font-size:1.9rem;color:#ffffff;background-color:rgba(12,16,22,.92);border:1px solid " + rgba(a, .65) + ";padding:.5rem 1.2rem .6rem;"; },
            btnHover: function (a) { return "background-image:linear-gradient(to top," + rgba(a, .55) + "," + rgba(a, .12) + ");border-color:" + a + ";"; },
            row: function () { return "background-color:rgba(14,18,24,.88);border:1px solid rgba(255,255,255,.08);padding:.8rem 1.2rem;"; },
            rowHover: function (a) { return "border-color:" + rgba(a, .7) + ";"; },
            rowSel: function (a) { return "background-image:linear-gradient(to top," + rgba(a, .45) + "," + rgba(a, .08) + ");border-color:" + a + ";"; },
            rowDeco: function (r, a, sel) { if (sel) corners(r, "#ffffff", "1rem", ".2rem"); },
            name: "font-family:" + F.demi + ";font-size:2.2rem;color:#ffffff;",
            meta: "font-family:" + F.norm + ";font-size:1.6rem;color:#9aa3aa;",
            pts: "font-family:" + F.demi + ";font-size:2.2rem;color:#ffffff;",
            secLabel: function (a) { return "font-family:" + F.demi + ";font-size:1.7rem;letter-spacing:.1rem;color:" + a + ";"; },
            secLine: function (a) { return "background-color:" + rgba(a, .5) + ";"; },
            key: "font-family:" + F.med + ";font-size:1.8rem;color:#9aa3aa;",
            val: "font-family:" + F.med + ";font-size:1.9rem;color:#e2e6e8;",
            launcher: function (a) { return "font-family:" + F.demi + ";font-size:2.7rem;color:#ffffff;background-color:rgba(10,13,18,.9);border:1px solid " + a + ";box-shadow:0 0 1.2rem " + rgba(a, .55) + ";padding:.5rem 1.8rem .7rem;"; },
            launcherHover: function (a) { return "background-image:linear-gradient(to top," + rgba(a, .6) + "," + rgba(a, .15) + ");"; },
            launcherDeco: function (l, a) { corners(l, "#ffffff", "1rem", ".2rem"); },
            upper: false
        },
        echo: {
            label: "ECHO",
            text: "#cfe6f2", dim: "#5f8aa0", warn: ORANGE,
            panel: function () { return "background-color:rgba(2,9,16,.94);border:1px solid " + rgba("#1abaff", .5) + ";box-shadow:inset 0 0 3rem " + rgba("#1abaff", .12) + ";padding:0 2.2rem 2rem;"; },
            deco: function (p) { corners(p, ORANGE, "1.8rem", ".25rem"); },
            header: "background-color:" + rgba("#1abaff", .14) + ";border-bottom:1px solid " + rgba("#1abaff", .5) + ";margin:0 -2.2rem 1.2rem;padding:1.2rem 2.2rem;",
            title: "font-family:" + F.demi + ";font-size:3rem;letter-spacing:.4rem;color:" + CYAN + ";",
            sub: "font-family:" + F.med + ";font-size:1.7rem;letter-spacing:.2rem;color:" + GREY + ";",
            btn: function () { return "font-family:" + F.med + ";font-size:1.7rem;letter-spacing:.15rem;color:" + CYAN + ";background-color:rgba(2,9,16,.6);border:1px solid " + rgba("#1abaff", .45) + ";padding:.6rem 1.2rem;"; },
            btnHover: function () { return "color:" + ORANGE + ";border-color:" + ORANGE + ";background-color:" + rgba("#f5a623", .12) + ";"; },
            row: function () { return "background-color:rgba(6,20,32,.6);border-bottom:1px solid " + rgba("#1abaff", .2) + ";border-left:.3rem solid rgba(0,0,0,0);padding:.8rem 1.2rem;"; },
            rowHover: function () { return "border-left-color:" + rgba("#f5a623", .5) + ";"; },
            rowSel: function () { return "background-color:" + rgba("#f5a623", .1) + ";border-left-color:" + ORANGE + ";"; },
            rowDeco: function (r, a, sel) { if (sel) corners(r, ORANGE, ".9rem", ".2rem"); },
            name: "font-family:" + F.med + ";font-size:2.1rem;color:#e8f6ff;",
            meta: "font-family:" + F.norm + ";font-size:1.5rem;letter-spacing:.1rem;color:#5f8aa0;",
            pts: "font-family:" + F.num + ";font-size:2.1rem;color:" + CYAN + ";",
            secLabel: function () { return "font-family:" + F.med + ";font-size:1.5rem;letter-spacing:.3rem;color:" + CYAN + ";"; },
            secLine: function () { return "background-color:" + rgba("#1abaff", .25) + ";"; },
            secPrefix: "// ",
            key: "font-family:" + F.med + ";font-size:1.7rem;letter-spacing:.1rem;color:#5f8aa0;",
            val: "font-family:" + F.med + ";font-size:1.9rem;color:#cfe6f2;",
            launcher: function () { return "font-family:" + F.demi + ";font-size:2.3rem;letter-spacing:.4rem;color:" + CYAN + ";background-color:rgba(2,9,16,.85);border:1px solid " + rgba("#1abaff", .6) + ";padding:.8rem 2rem;"; },
            launcherHover: function () { return "color:" + ORANGE + ";border-color:" + ORANGE + ";"; },
            launcherDeco: function (l) { corners(l, ORANGE, "1.1rem", ".25rem"); },
            upper: true
        },
        classic: {
            label: "Classic",
            text: "#f2efe6", dim: "#8d8a80", warn: "#ffc72c",
            panel: function () { return "background-color:rgba(10,10,10,.95);border:.3rem solid #000000;box-shadow:0 0 0 .2rem #ffc72c;padding:0 2.2rem 2rem;"; },
            header: "background-color:#ffc72c;margin:0 -2.2rem 1.2rem;padding:1rem 2.2rem;",
            title: "font-family:" + F.demi + ";font-size:3.4rem;letter-spacing:.2rem;color:#111111;",
            sub: "font-family:" + F.demi + ";font-size:1.8rem;color:#3a2d00;",
            closeOnHeader: "color:#111111;border-color:#111111;background-color:rgba(0,0,0,0);",
            btn: function () { return "font-family:" + F.demi + ";font-size:1.8rem;letter-spacing:.1rem;color:#ffc72c;background-color:#1a1a1a;border:.2rem solid #ffc72c;padding:.5rem 1.2rem;"; },
            btnHover: function () { return "background-color:#ffc72c;color:#111111;"; },
            row: function () { return "background-color:#161616;border-left:.5rem solid #333333;padding:.8rem 1.2rem;"; },
            rowHover: function () { return "border-left-color:#8a6d16;"; },
            rowSel: function () { return "background-color:#2a2310;border-left-color:#ffc72c;"; },
            name: "font-family:" + F.demi + ";font-size:2.2rem;color:#f2efe6;",
            nameSel: "color:#ffc72c;",
            meta: "font-family:" + F.med + ";font-size:1.6rem;color:#8d8a80;",
            pts: "font-family:" + F.demi + ";font-size:2.2rem;color:#111111;background-color:#ffc72c;padding:0 .8rem;",
            secLabel: function () { return "font-family:" + F.demi + ";font-size:1.8rem;letter-spacing:.2rem;color:#ffc72c;"; },
            secLine: function () { return "background-color:#ffc72c;height:.2rem;"; },
            key: "font-family:" + F.demi + ";font-size:1.8rem;color:#8d8a80;",
            val: "font-family:" + F.med + ";font-size:1.9rem;color:#f2efe6;",
            launcher: function () { return "font-family:" + F.demi + ";font-size:2.6rem;letter-spacing:.2rem;color:#111111;background-color:#ffc72c;border:.3rem solid #111111;box-shadow:0 0 0 .2rem #ffc72c;padding:.5rem 1.8rem .6rem;"; },
            launcherHover: function () { return "background-color:#ffe07a;"; },
            upper: true
        }
    };
    var THEME_ORDER = ["native", "tree", "echo", "classic"];

    // ------------------------------------------------------------ transport
    function req(method, path, body, cb) {
        var x;
        try {
            x = new XMLHttpRequest();
            x.open(method, BASE + path, true);
            x.timeout = 2500;
        } catch (e) { cb(null); return; }
        x.onload = function () {
            var d = null;
            try { d = JSON.parse(x.responseText); } catch (e) { d = null; }
            cb(x.status === 200 ? d : null);
        };
        x.onerror = x.ontimeout = function () { cb(null); };
        try { x.send(body ? JSON.stringify(body) : null); } catch (e) { cb(null); }   // text/plain: no preflight
    }
    var traceCount = 0, traceQueue = [], traceBusy = false;
    function trace(kind, data) {
        if (traceCount++ > 220) return;
        traceQueue.push({ kind: kind, data: data });
        flushTrace();
    }
    function flushTrace() {
        if (traceBusy || !traceQueue.length) return;
        traceBusy = true;
        req("POST", "/trace", traceQueue[0], function (r) {
            traceBusy = false;
            if (r) { traceQueue.shift(); flushTrace(); }
            else global.setTimeout(flushTrace, 3000);
        });
    }

    // ------------------------------------------------------------ helpers
    var ui = { host: null, launcher: null, panel: null, open: false, data: null, selected: null, sig: "",
               timer: 0, waitFor: 0, notice: null, offline: false, tree: null, treeKey: "", theme: DEFAULT_THEME };
    try { var saved = global.localStorage.getItem("SkillSaverTheme"); if (THEMES[saved]) ui.theme = saved; } catch (e) { /* no storage */ }

    function T() { return THEMES[ui.theme] || THEMES.native; }
    function acc() { return ui.tree || CYAN; }
    function up(s) { return T().upper ? String(s).toUpperCase() : s; }
    function el(tag, css, text) {
        var e = document.createElement(tag);
        if (css) e.style.cssText = css;
        if (text !== undefined && text !== null) e.textContent = text;
        return e;
    }
    function corners(box, color, size, width) {
        var s = size || "1rem", w = (width || "2px") + " solid " + color;
        [["top:0;left:0;", "border-top:" + w + ";border-left:" + w],
         ["top:0;right:0;", "border-top:" + w + ";border-right:" + w],
         ["bottom:0;left:0;", "border-bottom:" + w + ";border-left:" + w],
         ["bottom:0;right:0;", "border-bottom:" + w + ";border-right:" + w]].forEach(function (c) {
            box.appendChild(el("div", "position:absolute;width:" + s + ";height:" + s + ";pointer-events:none;" + c[0] + c[1] + ";"));
        });
    }
    function stopEvents(node) {
        ["mousedown", "mouseup", "click", "dblclick", "wheel", "mousewheel", "mousemove", "contextmenu"].forEach(function (t) {
            node.addEventListener(t, function (ev) { ev.stopPropagation(); });
        });
    }
    // element with a base style and a hover style (hover css is appended to the base css)
    function hoverable(e, base, hover, off) {
        e.__base = base; e.__hover = hover;
        e.style.cssText = base;
        e.__extra = "";
        e.addEventListener("mouseenter", function () { if (!e.__off) e.style.cssText = e.__base + e.__hover + e.__extra; });
        e.addEventListener("mouseleave", function () { e.style.cssText = e.__base + e.__extra; });
        return e;
    }

    var BTN_LAYOUT = "position:relative;margin:0 .7rem .7rem 0;text-align:center;white-space:nowrap;cursor:pointer;pointer-events:auto;box-sizing:border-box;";
    function button(label, onClick, wide) {
        var t = T(), a = acc();
        var b = el("div", "", up(label));
        hoverable(b, BTN_LAYOUT + "flex:" + (wide ? "1 1 auto" : "0 0 auto") + ";" + t.btn(a), t.btnHover(a));
        b.addEventListener("click", function (ev) { ev.stopPropagation(); if (!b.__off) onClick(b); });
        return b;
    }
    function setDisabled(b, off) {
        b.__off = !!off;
        b.__base = b.__base.replace(/opacity:[^;]*;/, "") + (off ? "opacity:.35;cursor:default;" : "");
        b.style.cssText = b.__base;
    }
    function confirmButton(label, ask, run) {
        var b = button(label, function () {
            if (b.__armed) { disarm(); run(); return; }
            b.__armed = true; b.textContent = up(ask); b.__extra = "color:" + T().warn + ";"; b.style.cssText = b.__base + b.__extra;
            b.__t = global.setTimeout(disarm, 3000);
        }, true);
        function disarm() { b.__armed = false; global.clearTimeout(b.__t); b.textContent = up(label); b.__extra = ""; b.style.cssText = b.__base; }
        return b;
    }
    function section(box, title) {
        var t = T(), a = acc();
        var r = el("div", "display:flex;flex-direction:row;align-items:center;padding:1.3rem 0 .5rem;");
        r.appendChild(el("div", "margin-right:1rem;white-space:nowrap;" + t.secLabel(a), (t.secPrefix || "") + up(title)));
        r.appendChild(el("div", "flex:1 1 auto;height:1px;" + t.secLine(a)));
        box.appendChild(r);
    }

    // ------------------------------------------------------------ launcher + panel
    function showLauncher(host) {
        if (ui.host === host && ui.launcher && ui.launcher.parentNode) return;
        hideAll();
        ui.host = host;
        buildLauncher();
        if (ui.reopen) { ui.reopen = false; openPanel(); }
    }
    function buildLauncher() {
        if (ui.launcher && ui.launcher.parentNode) ui.launcher.parentNode.removeChild(ui.launcher);
        var t = T(), a = acc();
        var l = el("div", "", up("Build Saver"));
        l.id = "SkillSaver_Launcher_v1";
        // under "Points Invested", right aligned like the tree title
        var pos = "position:absolute;right:2.2%;top:24%;z-index:60;cursor:pointer;pointer-events:auto;white-space:nowrap;text-align:center;min-width:22rem;box-sizing:border-box;";
        hoverable(l, pos + t.launcher(a) + (ui.open ? t.launcherHover(a) : ""), t.launcherHover(a));
        if (t.launcherDeco) t.launcherDeco(l, a);
        l.addEventListener("click", function (ev) { ev.stopPropagation(); ui.open ? closePanel() : openPanel(); });
        stopEvents(l);
        ui.host.appendChild(l);
        ui.launcher = l;
    }
    function hideAll() {
        closePanel();
        if (ui.launcher && ui.launcher.parentNode) ui.launcher.parentNode.removeChild(ui.launcher);
        ui.launcher = null; ui.host = null;
    }
    function openPanel() {
        if (!ui.host) return;
        closePanel();
        var p = el("div", "");
        p.id = "SkillSaver_Panel_v1";
        stopEvents(p);
        ui.host.appendChild(p);
        ui.panel = p; ui.open = true; ui.sig = "";
        stylePanel();
        p.appendChild(el("div", "padding:1rem;" + T().meta, "Reading saved builds ..."));
        buildLauncher();
        poll();
    }
    function stylePanel() {
        var t = T();
        // left side over the character model, between tab bar and hint bar; the skill tree stays visible
        ui.panel.style.cssText = "position:absolute;left:1.6%;top:11.5%;width:34%;height:76%;display:flex;flex-direction:column;" +
            "z-index:59;pointer-events:auto;box-sizing:border-box;overflow:hidden;color:" + t.text + ";" + t.panel(acc());
    }
    function closePanel() {
        var was = ui.open;
        ui.open = false;
        stopKb();
        ui.rename = null; ui.renameApi = null;
        global.clearTimeout(ui.timer);
        if (ui.panel && ui.panel.parentNode) ui.panel.parentNode.removeChild(ui.panel);
        ui.panel = null;
        if (was && ui.host) buildLauncher();
    }
    function nextTheme() {
        var i = THEME_ORDER.indexOf(ui.theme);
        ui.theme = THEME_ORDER[(i + 1) % THEME_ORDER.length];
        try { global.localStorage.setItem("SkillSaverTheme", ui.theme); } catch (e) { /* no storage */ }
        trace("theme", ui.theme);
        if (ui.panel) { stylePanel(); render(true); }
        buildLauncher();
    }

    function poll() {
        global.clearTimeout(ui.timer);
        if (!ui.open) return;
        req("GET", "/state", null, function (d) {
            if (!ui.open) return;
            ui.offline = !d;
            if (d) {
                ui.data = d;
                var done = d.result ? d.result.done || 0 : 0;
                if (ui.waitFor && done >= ui.waitFor) {
                    ui.notice = { text: d.result.msg, ok: d.result.ok };
                    ui.waitFor = 0;
                } else if (!ui.waitFor && ui.lastDone !== undefined && done > ui.lastDone && d.result.msg) {
                    ui.notice = { text: d.result.msg, ok: d.result.ok };      // e.g. rename typed in the keyboard window
                }
                ui.lastDone = done;
            }
            render();
            ui.timer = global.setTimeout(poll, ui.waitFor ? 300 : 1000);
        });
    }
    function send(action, id, name) {
        if (ui.waitFor) return;
        ui.notice = { text: "Working ...", ok: true, busy: true };
        render(true);
        req("POST", "/cmd", { action: action, id: id || "", name: name || "" }, function (r) {
            if (!r || !r.queued) {
                ui.notice = { text: "Not sent: " + ((r && r.error) || "Build Saver mod not reachable"), ok: false };
                render(true);
                return;
            }
            ui.waitFor = r.id;
            poll();
        });
    }
    function charName(k) { return CHAR[k] || k || "?"; }

    function render(force) {
        var p = ui.panel, d = ui.data, t = T(), a = acc();
        if (!p) return;
        var sig = JSON.stringify([ui.offline, d && d.builds, d && d.undo, d && d.character, d && d.points,
            d && d.gear_check, d && d.enabled, ui.selected, ui.notice, ui.waitFor, ui.tree, ui.theme]);
        if (!force && sig === ui.sig) return;            // nothing changed: keep scroll position
        if (!force && ui.rename && ui.renameApi && ui.renameApi.field.parentNode) return;   // typing: keep the field
        ui.sig = sig;
        var listScroll = 0, detScroll = 0;
        var oldList = p.querySelector("#SkillSaver_List_v1"), oldDet = p.querySelector("#SkillSaver_Detail_v1");
        if (oldList) listScroll = oldList.scrollTop;
        if (oldDet) detScroll = oldDet.scrollTop;
        while (p.firstChild) p.removeChild(p.firstChild);
        if (t.deco) t.deco(p, a);

        // header
        var head = el("div", "position:relative;display:flex;flex-direction:row;align-items:flex-start;flex-shrink:0;" + (t.header || "padding-bottom:1rem;"));
        var titles = el("div", "display:flex;flex-direction:column;flex:1 1 auto;");
        titles.appendChild(el("div", "line-height:1.1;" + t.title, up("Build Saver")));
        var subTxt = d && d.character ? charName(d.character) + (d.points !== null && d.points !== undefined ? "   -   " + d.points + " " + up("points") : "") : "";
        titles.appendChild(el("div", t.sub, subTxt));
        head.appendChild(titles);
        var tools = el("div", "display:flex;flex-direction:row;align-items:flex-start;");
        var sBtn = button("Style", nextTheme);
        var x = button("X", closePanel);
        [sBtn, x].forEach(function (b) {
            b.__base += "margin:0 0 0 .7rem;padding:.3rem 1rem;font-size:1.6rem;" + (t.closeOnHeader || "");
            b.style.cssText = b.__base;
            tools.appendChild(b);
        });
        sBtn.title = "Style: " + t.label;
        head.appendChild(tools);
        p.appendChild(head);

        if (ui.offline || !d) {
            p.appendChild(el("div", "padding:1rem;white-space:normal;" + t.val + "color:" + BAD + ";",
                "The Build Saver mod does not answer. Check that Build Saver is enabled in the mod manager."));
            return;
        }
        if (!d.enabled) {
            p.appendChild(el("div", "padding:1rem;" + t.val + "color:" + BAD + ";", "Build Saver is disabled in the mod manager."));
            return;
        }

        // toolbar
        var bar = el("div", "display:flex;flex-direction:row;flex-wrap:wrap;flex-shrink:0;");
        var bNew = button("Save new", function () { send("save"); }, true);
        var bUndo = confirmButton("Undo last load", "Click again: undo", function () { send("undo"); });
        var bReset = confirmButton("Reset tree", "Click again: reset", function () { send("reset"); });
        setDisabled(bNew, !d.in_game || ui.waitFor);
        setDisabled(bUndo, !d.undo || !d.in_game || ui.waitFor);
        setDisabled(bReset, !d.in_game || ui.waitFor);
        bar.appendChild(bNew); bar.appendChild(bUndo); bar.appendChild(bReset);
        p.appendChild(bar);

        // status line
        var n = ui.notice;
        if (n) p.appendChild(el("div", "min-height:2.4rem;white-space:normal;flex-shrink:0;padding:.2rem .2rem .6rem;" + t.meta +
            "color:" + (!n ? t.dim : n.busy ? t.warn : n.ok ? OK : BAD) + ";",
            n ? n.text : "Load sets skills and gear. Load, Overwrite, Delete and Reset: click twice."));

        // build list: current character first
        var builds = (d.builds || []).slice();
        var me = d.character || "";
        builds.sort(function (x1, x2) { return (x1.char === me ? 0 : 1) - (x2.char === me ? 0 : 1); });
        if (ui.selected && !builds.some(function (b) { return b.id === ui.selected; })) ui.selected = null;

        var lhead = el("div", "flex-shrink:0;");
        section(lhead, "Saved builds  (" + builds.length + ")");
        p.appendChild(lhead);
        // more room for the list (v4.0): it takes ~60 % of the height, the details below are compact
        var list = el("div", "display:flex;flex-direction:column;overflow-y:auto;overflow-x:hidden;padding:.3rem .6rem .3rem 0;" +
            (ui.rename ? "flex:0 1 auto;min-height:7rem;max-height:13rem;" : "flex:0 0 auto;min-height:10rem;"));
        list.id = "SkillSaver_List_v1";
        if (!builds.length) list.appendChild(el("div", "padding:1rem;" + t.meta, "No saved builds yet - press 'Save new'."));
        builds.forEach(function (b) {
            var other = me && b.char && b.char !== me;
            var sel = b.id === ui.selected;
            var row = el("div", "");
            var base = "position:relative;display:flex;flex-direction:row;align-items:center;margin:0 0 .3rem 0;cursor:pointer;flex-shrink:0;box-sizing:border-box;" +
                t.row(a) + "padding-top:.3rem;padding-bottom:.35rem;" + (sel ? t.rowSel(a) : "") + (other ? "opacity:.45;" : "");
            hoverable(row, base, sel ? "" : t.rowHover(a));
            var txt = el("div", "display:flex;flex-direction:column;flex:1 1 auto;min-width:0;");
            txt.appendChild(el("div", "white-space:nowrap;overflow:hidden;text-overflow:ellipsis;" + t.name + "font-size:1.9rem;" + (sel ? (t.nameSel || "color:#ffffff;") : ""), b.name));
            var sub = [b.action_skill || "", b.saved ? b.saved.slice(0, 16) : ""];
            if (other) sub.unshift(charName(b.char));
            txt.appendChild(el("div", "white-space:nowrap;overflow:hidden;text-overflow:ellipsis;" + t.meta + "font-size:1.3rem;",
                sub.filter(function (s) { return s; }).join("   -   ")));
            row.appendChild(txt);
            row.appendChild(el("div", "margin-left:1rem;" + t.pts, String(b.points)));
            if (t.rowDeco) t.rowDeco(row, a, sel);
            row.addEventListener("click", function (ev) { ev.stopPropagation(); ui.selected = b.id; render(true); });
            list.appendChild(row);
        });
        p.appendChild(list);

        // selected build: actions + details
        var selB = null, det = null;
        builds.forEach(function (b) { if (b.id === ui.selected) selB = b; });
        if (selB) {
            var other = me && selB.char && selB.char !== me;
            var acts = el("div", "display:flex;flex-direction:row;flex-wrap:wrap;flex-shrink:0;padding-top:.6rem;");
            var bLoad = confirmButton("Load", "Click again: load", function () { send("load", selB.id); });
            var bOver = confirmButton("Overwrite", "Click again: overwrite", function () { send("overwrite", selB.id); });
            var bDel = confirmButton("Delete", "Click again: delete", function () { send("delete", selB.id); });
            var bRen = button("Rename", function () { ui.rename = { id: selB.id, text: selB.name || "", shift: !selB.name }; render(true); }, true);
            setDisabled(bLoad, other || !d.in_game || ui.waitFor);
            setDisabled(bOver, other || !d.in_game || ui.waitFor);
            setDisabled(bDel, ui.waitFor);
            setDisabled(bRen, ui.waitFor);
            acts.appendChild(bLoad); acts.appendChild(bOver); acts.appendChild(bRen); acts.appendChild(bDel);
            p.appendChild(acts);
            if (other) p.appendChild(el("div", "flex-shrink:0;padding-bottom:.6rem;" + t.meta + "color:" + t.warn + ";",
                "This build belongs to " + charName(selB.char) + "."));
            if (ui.rename && ui.rename.id !== selB.id) { stopKb(); ui.rename = null; ui.renameApi = null; }   // another build selected
            if (ui.rename) { p.appendChild(editorView(selB)); list.scrollTop = listScroll; return; }
            if (GEAR_LAYOUT !== "list") p.appendChild(detailTabs(selB));
            det = el("div", "display:flex;flex-direction:column;overflow-y:auto;overflow-x:hidden;flex:0 0 auto;min-height:6rem;padding:0 .8rem .4rem 0;");
            det.id = "SkillSaver_Detail_v1";
            if (GEAR_LAYOUT === "list") details(det, selB, d.gear_check);
            else if (ui.tab === "gear") gearView(det, selB, d.gear_check);
            else if (ui.tab === "notes") notesView(det, selB);
            else skillsView(det, selB);
            compact(det, DETAIL_SCALE);
            p.appendChild(det);
            det.scrollTop = detScroll;
        }
        fitLayout(p, list, det || null);
        list.scrollTop = listScroll;
        if (det) det.scrollTop = detScroll;
    }

    // The game's UI engine does not stretch flex children reliably, so the build list and the details get
    // explicit heights: everything else keeps its natural height, the rest of the panel is split between
    // the list (55 %) and the details (45 %); without a selected build the list takes all of it.
    function remPx() {
        try { var v = parseFloat(global.getComputedStyle(document.documentElement).fontSize); if (v > 0) return v; } catch (e) { /* fall back */ }
        return 10;
    }
    function fitLayout(p, list, det) {
        if (!p || !list || ui.rename) return;
        var min = 7 * remPx();
        list.style.boxSizing = "border-box";
        if (det) det.style.boxSizing = "border-box";
        function set(lh, dh) {
            list.style.height = lh + "px"; list.style.maxHeight = lh + "px";
            if (det) { det.style.height = dh + "px"; det.style.maxHeight = dh + "px"; }
        }
        // measures where the content really ends and corrects the heights so the last box ends exactly at the
        // panel's inner bottom edge (the bottom padding is taken to be the same as the top padding)
        function run() {
            if (!p.parentNode || !list.parentNode || ui.rename) return;
            var pr = p.getBoundingClientRect(), first = null;
            for (var i = 0; i < p.children.length; i++) {
                if (p.children[i].style.position !== "absolute") { first = p.children[i]; break; }
            }
            var pad = first ? first.getBoundingClientRect().top - pr.top : 2 * remPx();
            if (!(pad >= 0) || pad > pr.height / 4) pad = 2 * remPx();
            var last = det || list;
            var over = last.getBoundingClientRect().bottom - (pr.bottom - pad);
            var total = list.getBoundingClientRect().height + (det ? det.getBoundingClientRect().height : 0) - over;
            if (!(total > 0)) total = 0;
            if (total < (det ? 2 : 1) * min) total = (det ? 2 : 1) * min;
            var lh = det ? Math.round(total * 0.55) : Math.round(total);
            set(lh, det ? Math.max(min, Math.round(total - lh)) : 0);
            if ((ui.layoutLog = (ui.layoutLog || 0) + 1) <= 6) {
                var after = last.getBoundingClientRect().bottom;
                trace("layout", { panel: [Math.round(pr.top), Math.round(pr.bottom)], pad: Math.round(pad), over: Math.round(over),
                                  total: Math.round(total), lastBottomAfter: Math.round(after), rem: remPx() });
            }
        }
        set(min, min);
        run();
        global.setTimeout(run, 0);                       // again after the engine has laid out the new content
        global.setTimeout(run, 120);
    }

    // ------------------------------------------------------------ rename: name field + on-screen keyboard
    // The game does not pass the keyboard to its menu. While this field is open the mod reads the keyboard
    // for it (kbd.py, /kb - can be switched off in the mod options); the on-screen keys always work.
    var KEYS = ["1234567890", "QWERTYUIOP", "ASDFGHJKL'", "ZXCVBNM-.!"];
    function editorView(b) {
        var t = T(), a = acc(), r = ui.rename, max = 60;
        var box = el("div", "display:flex;flex-direction:column;flex:1 1 auto;min-height:0;padding:.4rem .8rem .6rem 0;");
        section(box, "Rename build");
        var field = el("input", "font-family:" + F.med + ";font-size:2.4rem;color:#ffffff;background-color:rgba(3,16,26,.85);" +
            "border:1px solid " + a + ";padding:.5rem .9rem;margin:.2rem 0 .6rem;width:100%;box-sizing:border-box;pointer-events:auto;outline:none;");
        field.type = "text"; field.maxLength = max; field.value = r.text;
        function focusEnd() {
            try { field.focus(); var n = field.value.length; field.setSelectionRange(n, n); } catch (e) { /* no focus */ }
        }
        function set(v, fromKb) {
            r.text = v.slice(0, max);
            if (field.value !== r.text) field.value = r.text;
            focusEnd();
            if (!fromKb && r.kbOn) req("POST", "/kb", { cmd: "set", text: r.text }, function (k) { if (k) r.seq = k.seq; });
        }
        function done(save) {
            var id = r.id, name = r.text.replace(/\s+/g, " ").trim();
            stopKb();
            ui.rename = null; ui.renameApi = null;
            if (save && name && name !== b.name) send("rename", id, name);
            else render(true);
        }
        ui.renameApi = { set: set, done: done, field: field };
        field.addEventListener("input", function () { set(field.value); });
        field.addEventListener("keydown", function (ev) {
            ev.stopPropagation();
            if (ev.keyCode === 13) { ev.preventDefault(); done(true); }
            else if (ev.keyCode === 27) { ev.preventDefault(); done(false); }
        });
        ["keyup", "keypress"].forEach(function (k) { field.addEventListener(k, function (ev) { ev.stopPropagation(); }); });
        stopEvents(field);
        box.appendChild(field);
        box.appendChild(el("div", "flex-shrink:0;padding:0 0 .4rem;" + t.meta + "font-size:1.4rem;" + (r.kbErr ? "color:" + t.warn + ";" : ""),
            r.kbOn ? "Type on your keyboard (the first key replaces the old name) - Enter saves, Esc cancels."
                : r.kbErr ? "Keyboard typing is off (" + r.kbErr + ") - use the keys below." : "Starting keyboard ..."));
        if (!r.kb) {                                   // once per rename: ask the mod to read the keyboard for this field
            r.kb = true; r.seq = 0;
            req("POST", "/kb", { cmd: "start", text: r.text }, function (k) {
                if (ui.rename !== r) { if (k && k.active) req("POST", "/kb", { cmd: "stop" }, function () {}); return; }
                if (k && k.active) { r.kbOn = true; r.seq = k.seq; startKbPoll(); }
                else r.kbErr = (k && k.error) || "mod not reachable";
                render(true);
            });
        }
        var kb = el("div", "display:flex;flex-direction:column;flex-shrink:0;");
        KEYS.forEach(function (rowKeys) {
            var row = el("div", "display:flex;flex-direction:row;");
            rowKeys.split("").forEach(function (ch) {
                var k = button(ch, function () {
                    set(r.text + (r.shift ? ch : ch.toLowerCase()));
                    if (r.shift && /[A-Z]/.test(ch)) { r.shift = false; render(true); }      // one capital, like a phone keyboard
                });
                if (/[A-Z]/.test(ch)) k.textContent = r.shift ? ch : ch.toLowerCase();
                k.__base += "flex:1 1 0;min-width:0;margin:0 .25rem .25rem 0;padding:.2rem 0 .25rem;font-size:1.6rem;"; k.style.cssText = k.__base;
                row.appendChild(k);
            });
            kb.appendChild(row);
        });
        var last = el("div", "display:flex;flex-direction:row;");
        [["Shift", function () { r.shift = !r.shift; render(true); }, 1.4],
         ["Space", function () { set(r.text + " "); }, 3.6],
         ["Delete", function () { set(r.text.slice(0, -1)); }, 1.6],
         ["Clear", function () { set(""); r.shift = true; render(true); }, 1.4]].forEach(function (x) {
            var k = button(x[0], x[1]);
            k.__base += "flex:" + x[2] + " 1 0;min-width:0;margin:0 .25rem .25rem 0;padding:.2rem .2rem .25rem;font-size:1.5rem;" +
                (x[0] === "Shift" && r.shift ? "color:#ffffff;border-color:" + a + ";" : "");
            k.style.cssText = k.__base;
            last.appendChild(k);
        });
        kb.appendChild(last);
        box.appendChild(kb);
        var acts = el("div", "display:flex;flex-direction:row;flex-shrink:0;padding-top:.3rem;");
        acts.appendChild(button("Save name", function () { done(true); }, true));
        acts.appendChild(button("Cancel", function () { done(false); }, true));
        box.appendChild(acts);
        global.setTimeout(focusEnd, 0);
        return box;
    }

    function startKbPoll() {
        global.clearInterval(ui.kbTimer);
        ui.kbBusy = false;
        ui.kbTimer = global.setInterval(function () {
            var r = ui.rename;
            if (!r || !r.kbOn) { global.clearInterval(ui.kbTimer); return; }
            if (ui.kbBusy) return;
            ui.kbBusy = true;
            req("GET", "/kb", null, function (k) {
                ui.kbBusy = false;
                if (!k || ui.rename !== r || !ui.renameApi) return;
                if (k.seq > r.seq) { r.seq = k.seq; if (k.text !== r.text) ui.renameApi.set(k.text, true); }
                ui.renameApi.field.style.backgroundColor = k.fresh ? "rgba(26,120,170,.55)" : "rgba(3,16,26,.85)";
                if (k.end === "enter") ui.renameApi.done(true);
                else if (k.end === "esc") ui.renameApi.done(false);
                else if (!k.active) { r.kbOn = false; r.kbErr = k.error || "stopped"; render(true); }
            });
        }, 120);
    }
    function stopKb() {
        global.clearInterval(ui.kbTimer);
        if (ui.rename && ui.rename.kbOn) { ui.rename.kbOn = false; req("POST", "/kb", { cmd: "stop" }, function () {}); }
    }

    // details are drawn with the normal sizes, then scaled down (font sizes and vertical paddings in rem)
    var DETAIL_SCALE = 0.72;
    function compact(root, f) {
        var all = [root].concat(Array.prototype.slice.call(root.getElementsByTagName("*")));
        all.forEach(function (e) {
            var css = e.style.cssText;
            if (!css || css.indexOf("rem") < 0) return;
            css = css.replace(/(font-size|padding-top|padding-bottom|margin-bottom|min-height|line-height):\s*([\d.]+)rem/g,
                function (m, k, v) { return k + ":" + (parseFloat(v) * f).toFixed(2) + "rem"; });
            css = css.replace(/padding:\s*([\d.]+)rem\s+([\d.]+)rem\s+([\d.]+)rem/g,
                function (m, t1, r1, b1) { return "padding:" + (t1 * f).toFixed(2) + "rem " + r1 + "rem " + (b1 * f).toFixed(2) + "rem"; });
            e.style.cssText = css;
            if (e.__base) e.__base = css;               // buttons keep the scaled size on hover
        });
    }

    var MARK = { worn: OK, backpack: WARN, missing: BAD };
    function line(box, label, value, dot) {
        var t = T();
        var r = el("div", "display:flex;flex-direction:row;align-items:center;padding:.25rem 0;");
        if (dot !== undefined) r.appendChild(el("div", "width:1rem;height:1rem;min-width:1rem;margin-right:.9rem;background-color:" + (MARK[dot] || "transparent") + ";"));
        r.appendChild(el("div", "width:16rem;min-width:16rem;" + t.key, label));
        r.appendChild(el("div", "white-space:normal;flex:1 1 auto;" + t.val, value));
        box.appendChild(r);
    }
    function details(box, b, gearCheck) {
        section(box, "Action Skill");
        line(box, "Action Skill", b.action_skill || "-");
        line(box, "Augment", b.augments.length ? b.augments.join(", ") : "-");
        line(box, "Capstone", b.capstones.length ? b.capstones.join(", ") : "-");
        section(box, "Specialization");
        if (b.spec.length) b.spec.forEach(function (s) { line(box, s.tree, s.name); });
        else line(box, "", "-");
        section(box, "Gear");
        if (gearCheck) box.appendChild(el("div", "padding:0 0 .3rem;" + T().meta, "green = worn    yellow = in backpack    red = not found"));
        if (b.gear.length) b.gear.forEach(function (g) { line(box, g.slot, g.label, gearCheck ? (g.mark || "") : undefined); });
        else line(box, "", "(not in this save - use Overwrite)");
        if (b.firmware.length) {
            section(box, "Firmware");
            b.firmware.forEach(function (f) { line(box, f.set, f.count + "x  " + f.slots.join(", ")); });
        }
        if (b.notes) {
            section(box, "Notes");
            box.appendChild(el("div", "white-space:pre-line;" + T().val, b.notes));
        }
    }

    // ------------------------------------------------------------ details with tabs (Skills | Gear | Notes)
    var GEAR_LAYOUT = "tiles";          // "list" (v1.3), "tiles" or "grouped"
    ui.tab = "skills";
    var ELEMENT = { radiation: "#d4e83a", incendiary: "#ff7a2e", fire: "#ff7a2e", shock: "#3fa9ff", cryo: "#8fe3ff",
                    corrosive: "#9be22d", kinetic: GREY };
    var STATUS = { worn: [OK, "Worn"], backpack: [WARN, "Backpack"], missing: [BAD, "Missing"] };
    function splitLabel(label) {                         // "Divided Glow  (Radiation)" -> name + element
        var m = /^(.*?)\s+\(([^)]+)\)$/.exec(label || "");
        return m ? { name: m[1], element: m[2] } : { name: label || "-", element: "" };
    }
    function fwBySlot(b) {
        var out = {};
        (b.firmware || []).forEach(function (f) { f.slots.forEach(function (s) { out[s] = f.set; }); });
        return out;
    }
    function detailTabs(b) {
        var bar = el("div", "display:flex;flex-direction:row;flex-shrink:0;margin-top:.4rem;border-bottom:1px solid " + rgba("#3f769d", .5) + ";");
        var tabs = [["skills", "Skills"], ["gear", "Gear (" + b.gear.length + ")"]];
        if (b.notes) tabs.push(["notes", "Notes"]);              // only builds with notes from the desktop app
        else if (ui.tab === "notes") ui.tab = "skills";
        tabs.forEach(function (t) {
            var on = ui.tab === t[0];
            // like the menu tabs: blue text, selected = white text on a cyan gradient with a bottom line
            var tab = el("div", "");
            hoverable(tab, "font-family:" + F.med + ";font-size:1.7rem;padding:.35rem 1.3rem .45rem;cursor:pointer;pointer-events:auto;" +
                (on ? "color:#ffffff;background-image:linear-gradient(to top," + rgba("#1abaff", .45) + "," + rgba("#1abaff", .05) + ");border-bottom:.25rem solid " + CYAN + ";"
                    : "color:" + CYAN + ";border-bottom:.25rem solid rgba(0,0,0,0);"), on ? "" : "color:#ffffff;");
            tab.textContent = up(t[1]);
            tab.addEventListener("click", function (ev) { ev.stopPropagation(); ui.tab = t[0]; render(true); });
            bar.appendChild(tab);
        });
        return bar;
    }
    function skillsView(box, b) {
        section(box, "Action Skill");
        line(box, "Action Skill", b.action_skill || "-");
        line(box, "Augment", b.augments.length ? b.augments.join(", ") : "-");
        line(box, "Capstone", b.capstones.length ? b.capstones.join(", ") : "-");
        section(box, "Specialization");
        if (b.spec.length) b.spec.forEach(function (s) { line(box, s.tree, s.name); });
        else line(box, "", "-");
    }
    function notesView(box, b) {           // read only - notes are written in the desktop app
        box.appendChild(el("div", "white-space:pre-line;padding-top:.6rem;" + T().val, b.notes || ""));
    }
    function chip(text, color, filled) {
        return el("div", "font-family:" + F.med + ";font-size:1.4rem;letter-spacing:.1rem;padding:.1rem .7rem;margin-right:.6rem;white-space:nowrap;" +
            (filled ? "color:#03101a;background-color:" + color + ";" : "color:" + color + ";border:1px solid " + color + ";"), up(text).toUpperCase());
    }
    function firmwareSummary(box, b) {
        if (!b.firmware.length) return;
        var r = el("div", "display:flex;flex-direction:row;flex-wrap:wrap;align-items:center;padding:1rem 0 .2rem;");
        r.appendChild(el("div", "margin-right:1rem;" + T().key, "Firmware"));
        b.firmware.forEach(function (f) { r.appendChild(chip(f.set + "  x" + f.count, f.count >= 3 ? CYAN : STEEL, f.count >= 3)); });
        box.appendChild(r);
    }
    function legend(box) {
        var r = el("div", "display:flex;flex-direction:row;align-items:center;padding:.6rem 0 .2rem;");
        ["worn", "backpack", "missing"].forEach(function (k) {
            r.appendChild(el("div", "width:1rem;height:1rem;margin-right:.5rem;background-color:" + STATUS[k][0] + ";"));
            r.appendChild(el("div", "margin-right:1.6rem;" + T().meta, STATUS[k][1]));
        });
        box.appendChild(r);
    }
    function gearView(box, b, gearCheck) {
        if (!b.gear.length) { box.appendChild(el("div", "padding-top:1rem;" + T().meta, "No gear in this save - use Overwrite.")); return; }
        firmwareSummary(box, b);
        if (gearCheck) legend(box);
        var fws = fwBySlot(b);
        if (GEAR_LAYOUT === "tiles") return gearTiles(box, b, gearCheck, fws);
        var weapons = b.gear.filter(function (g) { return /^weapon/i.test(g.slot); });
        var equip = b.gear.filter(function (g) { return !/^weapon/i.test(g.slot); });
        if (weapons.length) { section(box, "Weapons"); weapons.forEach(function (g) { gearRow(box, g, gearCheck, fws); }); }
        if (equip.length) { section(box, "Equipment"); equip.forEach(function (g) { gearRow(box, g, gearCheck, fws); }); }
    }
    // grouped: one row per item, status as a chip on the right
    function gearRow(box, g, gearCheck, fws) {
        var t = T(), it = splitLabel(g.label), st = gearCheck ? STATUS[g.mark] : null;
        var r = el("div", "display:flex;flex-direction:row;align-items:center;padding:.5rem .8rem;margin-bottom:.4rem;background-color:rgba(10,30,44,.6);");
        r.appendChild(el("div", "width:13rem;min-width:13rem;" + t.key, g.slot));
        var mid = el("div", "display:flex;flex-direction:column;flex:1 1 auto;min-width:0;");
        mid.appendChild(el("div", "white-space:nowrap;overflow:hidden;text-overflow:ellipsis;" + t.val, it.name));
        var sub = el("div", "display:flex;flex-direction:row;");
        if (it.element) sub.appendChild(el("div", "margin-right:1rem;" + t.meta + "color:" + (ELEMENT[it.element.toLowerCase()] || GREY) + ";", it.element));
        if (fws[g.slot]) sub.appendChild(el("div", t.meta, fws[g.slot]));
        if (sub.firstChild) mid.appendChild(sub);
        r.appendChild(mid);
        if (st) r.appendChild(chip(st[1], st[0], false));
        box.appendChild(r);
    }
    // tiles: two columns like inventory slots, status as a coloured bar on the left
    function gearTiles(box, b, gearCheck, fws) {
        var t = T();
        var grid = el("div", "display:flex;flex-direction:row;flex-wrap:wrap;justify-content:space-between;padding-top:.8rem;");
        b.gear.forEach(function (g) {
            var it = splitLabel(g.label), st = gearCheck ? STATUS[g.mark] : null;
            var tile = el("div", "width:49%;box-sizing:border-box;margin-bottom:.8rem;padding:.6rem 1rem .7rem;background-color:rgba(10,30,44,.75);" +
                "border-left:.3rem solid " + (st ? st[0] : STEEL) + ";");
            var top = el("div", "display:flex;flex-direction:row;align-items:center;");
            top.appendChild(el("div", "flex:1 1 auto;" + t.meta + "color:" + STEEL + ";", up(g.slot)));
            if (st) top.appendChild(el("div", t.meta + "font-size:1.3rem;color:" + st[0] + ";", st[1].toUpperCase()));
            tile.appendChild(top);
            tile.appendChild(el("div", "white-space:nowrap;overflow:hidden;text-overflow:ellipsis;" + t.val + "font-size:2rem;color:#dfe7ea;", it.name));
            var sub = el("div", "display:flex;flex-direction:row;min-height:1.8rem;");
            if (it.element) sub.appendChild(el("div", "margin-right:1rem;" + t.meta + "color:" + (ELEMENT[it.element.toLowerCase()] || GREY) + ";", it.element));
            if (fws[g.slot]) sub.appendChild(el("div", t.meta + "color:" + GREY + ";", fws[g.slot]));
            tile.appendChild(sub);
            grid.appendChild(tile);
        });
        box.appendChild(grid);
    }
    global.__SkillSaverPreview = function (layout, tab) { GEAR_LAYOUT = layout; ui.tab = tab; render(true); };

    // ------------------------------------------------------------ find the skill page
    var host = null;
    function isShown(w) {
        if (!w || !w.parentNode) return false;
        if (typeof w.IsActivated === "boolean") return w.IsActivated;
        try { var r = w.getBoundingClientRect(); return r.width > 0 && r.height > 0; } catch (e) { return false; }
    }
    function findHost() {
        if (host && host.parentNode) return host;
        var list = document.getElementsByTagName(HOST_TAG);
        host = list.length ? list[0] : null;
        return host;
    }
    function treeColour(w) {
        var cls = String(w.className || "").split(/\s+/);
        for (var i = 0; i < cls.length; i++) if (TREE[cls[i]]) return [cls[i], TREE[cls[i]]];
        return ["", null];
    }
    function check() {
        var w = findHost();
        if (w && isShown(w)) {
            showLauncher(w);
            var tc = treeColour(w);
            if (tc[0] !== ui.treeKey) {                       // skill tree switched (Y / C)
                ui.treeKey = tc[0]; ui.tree = tc[1];
                if (ui.panel) { stylePanel(); render(true); }
                buildLauncher();
            }
        } else if (ui.host) {
            hideAll();
        }
    }
    // real keyboard while renaming: handled on the document (the text field itself may never get the focus)
    function onKey(ev) {
        if (!ui.rename || !ui.renameApi) return;
        ev.stopPropagation();
        if (ev.type !== "keydown") { ev.preventDefault(); return; }
        var api = ui.renameApi, r = ui.rename, k = ev.keyCode, ch = "";
        if (k === 13) { ev.preventDefault(); api.done(true); return; }
        if (k === 27) { ev.preventDefault(); api.done(false); return; }
        if (k === 8) { ev.preventDefault(); api.set(r.text.slice(0, -1)); return; }
        if (typeof ev.key === "string" && ev.key.length === 1) ch = ev.key;                 // respects the keyboard layout
        else if (k === 32) ch = " ";
        else if (k >= 48 && k <= 57) ch = String.fromCharCode(k);
        else if (k >= 65 && k <= 90) ch = ev.shiftKey ? String.fromCharCode(k) : String.fromCharCode(k + 32);
        else if (k === 189 || k === 173) ch = "-";
        else if (k === 190) ch = ".";
        if (ch && !ev.ctrlKey && !ev.altKey) { ev.preventDefault(); api.set(r.text + ch); }
    }
    ["keydown", "keypress", "keyup"].forEach(function (t) { document.addEventListener(t, onKey, true); });

    function start() {
        trace("start", { href: String(global.location && global.location.href), version: "4.0", theme: ui.theme });
        global.setInterval(check, 400);
    }
    // preview hook (outside the game only)
    global.__SkillSaverSetTheme = function (name) { if (THEMES[name]) { ui.theme = name; if (ui.panel) { stylePanel(); render(true); } if (ui.host) buildLauncher(); } };

    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
    else start();
})(window);
