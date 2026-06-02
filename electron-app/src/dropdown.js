'use strict';

class CustomSelect {
  constructor(container) {
    this.container = container;
    this._value = '';
    this._onChange = null;
    this._disabled = false;

    this.wrapper = document.createElement('div');
    this.wrapper.className = 'custom-select';

    this.trigger = document.createElement('div');
    this.trigger.className = 'custom-select-trigger';
    this.trigger.tabIndex = 0;

    this.textEl = document.createElement('span');
    this.textEl.className = 'custom-select-text';
    this.textEl.textContent = 'Sélectionner...';

    this.arrowEl = document.createElement('span');
    this.arrowEl.className = 'custom-select-arrow';
    this.arrowEl.innerHTML =
      '<svg width="12" height="8" viewBox="0 0 12 8"><path fill="currentColor" d="M6 8L0 0h12z"/></svg>';

    this.trigger.appendChild(this.textEl);
    this.trigger.appendChild(this.arrowEl);

    this.dropdown = document.createElement('div');
    this.dropdown.className = 'custom-select-dropdown';

    this.wrapper.appendChild(this.trigger);
    this.wrapper.appendChild(this.dropdown);

    this._onScroll = () => this.close();

    this.trigger.addEventListener('click', (e) => {
      e.stopPropagation();
      if (this._disabled) return;
      this.toggle();
    });

    this.trigger.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        if (this._disabled) return;
        this.toggle();
      }
      if (e.key === 'Escape') {
        this.close();
      }
    });

    this.dropdown.addEventListener('click', (e) => {
      e.stopPropagation();
    });

    this._outsideHandler = (e) => {
      if (!this.wrapper.contains(e.target)) {
        this.close();
      }
    };

    this._keydownHandler = (e) => {
      if (e.key === 'Escape') this.close();
    };

    document.addEventListener('click', this._outsideHandler);
    document.addEventListener('keydown', this._keydownHandler);

    container.appendChild(this.wrapper);
  }

  get value() { return this._value; }

  set value(v) {
    if (this._value === v) return;
    this._value = v;
    this.textEl.textContent = v || 'Sélectionner...';
    this.textEl.classList.toggle('placeholder', !v);
    this._highlightOption();
    if (this._onChange) this._onChange(v);
  }

  set onchange(fn) { this._onChange = fn; }

  get disabled() { return this._disabled; }

  set disabled(v) {
    this._disabled = v;
    this.wrapper.classList.toggle('disabled', v);
  }

  toggle() {
    if (this.dropdown.classList.contains('open')) {
      this.close();
    } else {
      this.open();
    }
  }

  open() {
    this._position();
    this.dropdown.classList.add('open');
    this.wrapper.classList.add('open');
    this.trigger.classList.add('open');
    requestAnimationFrame(() => {
      this.dropdown.scrollTop = 0;
    });
    document.getElementById('scroll-area').addEventListener('scroll', this._onScroll);
    window.addEventListener('resize', this._onScroll);
  }

  close() {
    this.dropdown.classList.remove('open');
    this.wrapper.classList.remove('open');
    this.trigger.classList.remove('open');
    document.getElementById('scroll-area').removeEventListener('scroll', this._onScroll);
    window.removeEventListener('resize', this._onScroll);
  }

  _position() {
    const rect = this.trigger.getBoundingClientRect();
    const spaceBelow = window.innerHeight - rect.bottom;
    const spaceAbove = rect.top;
    const dropdownHeight = Math.min(250, spaceBelow - 10);

    if (dropdownHeight >= 100 || spaceBelow >= spaceAbove) {
      this.dropdown.style.top = (rect.bottom + 4) + 'px';
      this.dropdown.style.bottom = 'auto';
      this.dropdown.style.maxHeight = Math.min(250, spaceBelow - 10) + 'px';
    } else {
      this.dropdown.style.bottom = (window.innerHeight - rect.top + 4) + 'px';
      this.dropdown.style.top = 'auto';
      this.dropdown.style.maxHeight = Math.min(250, spaceAbove - 10) + 'px';
    }
    this.dropdown.style.left = rect.left + 'px';
    this.dropdown.style.width = rect.width + 'px';
  }

  _highlightOption() {
    this.dropdown.querySelectorAll('.custom-select-option').forEach(el => {
      el.classList.toggle('selected', el.dataset.value === this._value);
    });
  }

  setOptions(options) {
    this.dropdown.innerHTML = '';
    for (const opt of options) {
      const el = document.createElement('div');
      el.className = 'custom-select-option';
      el.dataset.value = opt;
      el.textContent = opt;
      el.addEventListener('click', (e) => {
        e.stopPropagation();
        this.value = opt;
        this.close();
      });
      this.dropdown.appendChild(el);
    }
    this._highlightOption();
  }

  destroy() {
    document.removeEventListener('click', this._outsideHandler);
    document.removeEventListener('keydown', this._keydownHandler);
    this.wrapper.remove();
  }
}
