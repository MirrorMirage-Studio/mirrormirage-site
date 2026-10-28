/* MirrorMirage: эффекты сайта (кристаллы, меню-бургер, проявление блоков).
   Один файл без библиотек. Если он не загрузился, сайт работает как обычно. */
(function () {
  'use strict';

  /* ---------- Меню-бургер на телефоне ----------
     Кнопка переключает класс open у шапки и атрибут aria-expanded.
     Меню закрывают: Esc, клик по ссылке, расширение окна до компьютерной ширины. */
  function initMenu() {
    var header = document.querySelector('header.site');
    var button = header && header.querySelector('.menu-toggle');
    var nav = document.getElementById('site-nav');
    if (!header || !button || !nav) return;

    function setOpen(open) {
      header.classList.toggle('open', open);
      button.setAttribute('aria-expanded', open ? 'true' : 'false');
      button.setAttribute('aria-label', open ? 'Закрыть меню' : 'Меню');
    }

    button.addEventListener('click', function () {
      setOpen(!header.classList.contains('open'));
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && header.classList.contains('open')) {
        setOpen(false);
        button.focus();
      }
    });
    nav.addEventListener('click', function (e) {
      if (e.target.closest('a')) setOpen(false);
    });
    window.matchMedia('(min-width: 701px)').addEventListener('change', function (e) {
      if (e.matches) setOpen(false);
    });
  }

  initMenu();
  // Сюда в задачах 4 и 6 добавятся кристаллы и initReveal().
})();
