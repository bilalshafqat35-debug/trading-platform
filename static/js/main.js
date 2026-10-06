// ============ U1: TOAST NOTIFICATIONS ============
function closeToast(el) {
  if (!el) return;
  el.classList.add('hide');
  setTimeout(function () { el.remove(); }, 400);
}

document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('.toast').forEach(function (t, i) {
    setTimeout(function () {
      closeToast(t);
    }, 3500 + i * 200);
  });
});

// ============ U2: SKELETON LOADERS ============
document.addEventListener('DOMContentLoaded', function () {
  var coinsSkeleton = document.getElementById('coinsSkeleton');
  var coinsList = document.getElementById('coinsList');
  if (coinsSkeleton && coinsList) {
    setTimeout(function () {
      coinsSkeleton.style.display = 'none';
      coinsList.style.display = 'block';
    }, 1200);
  }

  var chartSpinner = document.getElementById('chartSpinner');
  if (chartSpinner) {
    setTimeout(function () {
      chartSpinner.classList.add('hidden');
    }, 1800);
  }
});

// ============ U11: LIVE PRICE + EXPECTED QUANTITY ============
document.addEventListener('DOMContentLoaded', function () {

  var priceBox = document.getElementById('livePriceValue');
  var symbolSelect = document.getElementById('tradeSymbol');
  var amountInput = document.getElementById('tradeAmount');
  var expectedQty = document.getElementById('expectedQty');
  var expectedQtyValue = document.getElementById('expectedQtyValue');

  if (!priceBox || !symbolSelect) return;

  var currentPrice = null;

  function fetchPrice() {
    var symbol = symbolSelect.value;
    fetch('/api/price/' + symbol + '/')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.error) {
          priceBox.innerHTML = '<span class="price-loading">Unavailable</span>';
          currentPrice = null;
          updateQuantity();
          return;
        }
        currentPrice = parseFloat(data.price);
        var formatted = '$' + currentPrice.toLocaleString('en-US', {
          minimumFractionDigits: 2,
          maximumFractionDigits: 6
        });
        priceBox.textContent = formatted;
        priceBox.classList.remove('updated');
        void priceBox.offsetWidth;
        priceBox.classList.add('updated');
        updateQuantity();
      })
      .catch(function () {
        priceBox.innerHTML = '<span class="price-loading">Error</span>';
        currentPrice = null;
      });
  }

  function updateQuantity() {
    if (!amountInput || !expectedQty || !expectedQtyValue) return;
    var amount = parseFloat(amountInput.value);
    if (!currentPrice || !amount || amount <= 0) {
      expectedQty.style.display = 'none';
      return;
    }
    var qty = amount / currentPrice;
    var unit = symbolSelect.value.replace('USD', '');
    expectedQtyValue.textContent = qty.toFixed(8) + ' ' + unit;
    expectedQty.style.display = 'block';
  }

  symbolSelect.addEventListener('change', function () {
    priceBox.innerHTML = '<span class="price-loading">Loading...</span>';
    fetchPrice();
    updateQuantity();
  });

  if (amountInput) {
    amountInput.addEventListener('input', updateQuantity);
  }

  fetchPrice();
  setInterval(fetchPrice, 5000);
});
// ============ U14: PASSWORD EYE TOGGLE ============
document.addEventListener('DOMContentLoaded', function () {
  var toggleButtons = document.querySelectorAll('.password-toggle');

  toggleButtons.forEach(function (btn) {
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      var wrapper = btn.closest('.password-wrapper');
      if (!wrapper) return;
      var input = wrapper.querySelector('input');
      if (!input) return;

      if (input.type === 'password') {
        input.type = 'text';
        btn.innerHTML = '<svg viewBox="0 0 24 24"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>';
        btn.setAttribute('aria-label', 'Hide password');
      } else {
        input.type = 'password';
        btn.innerHTML = '<svg viewBox="0 0 24 24"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>';
        btn.setAttribute('aria-label', 'Show password');
      }
    });
  });
});