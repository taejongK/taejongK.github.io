/* 화면 연출: 스크롤 등장 · 목차 현재 위치 · 상단 진행 바.
   JS가 없거나 모션 축소 설정이면 아무것도 숨기지 않는다 (CSS가 html.js-motion 일 때만 숨김). */
(function () {
  var root = document.documentElement;
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // 1) 읽기 진행 바 + 스크롤 시 네비 그림자
  var bar = document.createElement("div");
  bar.className = "progress";
  document.body.appendChild(bar);
  var nav = document.querySelector(".navbar");
  function onScroll() {
    var max = root.scrollHeight - root.clientHeight;
    bar.style.transform = "scaleX(" + (max > 0 ? root.scrollTop / max : 0) + ")";
    if (nav) nav.classList.toggle("scrolled", root.scrollTop > 4);
  }
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  // 인쇄할 때는 접힌 프로젝트 본문을 모두 펼친다
  window.addEventListener("beforeprint", function () {
    document.querySelectorAll("details").forEach(function (d) { d.open = true; });
  });

  // 프로젝트 본문 펼치기·접기: 높이를 부드럽게 늘이고 줄인다 (모션 축소 설정이면 기본 동작 그대로)
  if (!reduce && Element.prototype.animate) {
    document.querySelectorAll("details").forEach(function (d) {
      var body = d.querySelector(".work-body"), anim = null;
      if (!body) return;
      d.querySelector("summary").addEventListener("click", function (e) {
        e.preventDefault();
        var from = anim ? body.getBoundingClientRect().height : null;   // 도중에 다시 누르면 지금 높이에서 이어간다
        if (anim) anim.cancel();
        var opening = !d.open || d.classList.contains("closing");
        d.classList.toggle("closing", !opening);
        d.open = true;
        var full = body.scrollHeight;
        if (from === null) from = opening ? 0 : full;
        var to = opening ? full : 0;
        body.style.overflow = "hidden";
        anim = body.animate(
          [{ height: from + "px", opacity: opening ? Math.min(from / full, 1) : 1 },
           { height: to + "px", opacity: opening ? 1 : 0 }],
          { duration: (600 + Math.min(full, 1500) * 0.3) * (opening ? 1 : 0.7),   // 길수록 조금 더 천천히, 접기는 더 빨리
            easing: "cubic-bezier(.65, 0, .35, 1)" });
        anim.onfinish = function () {
          anim = null;
          body.style.overflow = "";
          if (!opening) { d.open = false; d.classList.remove("closing"); }
        };
      });
    });
  }

  if (!("IntersectionObserver" in window)) return;

  // 2) 스크롤 등장: 블록 단위로 한 번만
  if (!reduce) {
    root.classList.add("js-motion");
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
      });
    }, { rootMargin: "0px 0px -8% 0px" });
    document.querySelectorAll(
      ".sec-head, .statement, .prose, .card, .timeline, .tl-item, .bg-grid, .tools, .work, .contact-list, " +
      ".doc-detail > h2, .doc-detail > h3, .figure, .table-wrap, .diagram, .doc-detail > p, .doc-detail > ul"
    ).forEach(function (el) { el.classList.add("reveal"); io.observe(el); });
  }

  // 3) 목차·상단 메뉴에 현재 섹션 표시
  var links = {};
  document.querySelectorAll(".toc a[href^='#'], .navbar-links a[href^='#']").forEach(function (a) {
    links[decodeURIComponent(a.getAttribute("href").slice(1))] = a;
  });
  var heads = Object.keys(links).map(function (id) { return document.getElementById(id); }).filter(Boolean);
  if (!heads.length) return;
  var current = null;
  function pick() {
    var line = window.innerHeight * 0.25, hit = null;   // 첫 섹션 위(히어로)에서는 표시 없음
    heads.forEach(function (h) { if (h.getBoundingClientRect().top <= line) hit = h; });
    if (hit === current) return;
    if (current) links[current.id].classList.remove("active");
    if (hit) links[hit.id].classList.add("active");
    current = hit;
  }
  window.addEventListener("scroll", pick, { passive: true });
  pick();
})();
