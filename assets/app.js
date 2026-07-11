/* Terry Research — 共享交互脚本（无依赖，原生 JS）
 * 功能:
 *   1. 阅读进度条 (.read-progress) 随滚动更新宽度
 *   2. 回到顶部按钮 (.to-top) 滚动超过阈值后显隐
 *   3. 点击回到顶部平滑滚动
 *   4. 当前章节高亮 (.toc--side a.is-active)，基于 IntersectionObserver
 */
(function () {
  'use strict';

  var progress = document.querySelector('.read-progress');
  var toTop = document.querySelector('.to-top');

  function onScroll() {
    var doc = document.documentElement;
    var scrolled = doc.scrollTop || document.body.scrollTop || 0;
    var height = doc.scrollHeight - doc.clientHeight;
    var pct = height > 0 ? (scrolled / height) * 100 : 0;
    if (progress) progress.style.width = pct + '%';
    if (toTop) toTop.classList.toggle('is-visible', scrolled > 420);
  }

  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', onScroll);
  if (toTop) {
    toTop.addEventListener('click', function () {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }
  onScroll();

  // 章节高亮
  var links = Array.prototype.slice.call(
    document.querySelectorAll('.toc--side a[href^="#"]')
  );
  if (links.length && 'IntersectionObserver' in window) {
    var map = {};
    links.forEach(function (a) {
      var id = a.getAttribute('href').slice(1);
      if (id) map[id] = a;
    });
    var sections = Object.keys(map)
      .map(function (id) { return document.getElementById(id); })
      .filter(Boolean);
    if (sections.length) {
      var observer = new IntersectionObserver(function (entries) {
        entries.forEach(function (e) {
          if (e.isIntersecting) {
            links.forEach(function (l) { l.classList.remove('is-active'); });
            var active = map[e.target.id];
            if (active) active.classList.add('is-active');
          }
        });
      }, { rootMargin: '-15% 0px -75% 0px', threshold: 0 });
      sections.forEach(function (s) { observer.observe(s); });
    }
  }
})();
