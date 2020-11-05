// This code is based on William Imoh's eye-tracking alien demo, copyright 2018 William Imoh, 
// and used with permission.  Check it out!
// https://scotch.io/bar-talk/code-challenge-4-build-an-eye-tracking-alien-with-javascript
// https://scotch.io/bar-talk/build-an-eye-tracking-alien-with-javascript-solution-to-code-challenge-4

var stare = true;
var canLook = false;
var body = document.querySelector('body');
var pivvy = document.querySelector('.pivvy');

window.addEventListener('click', function () {
  if (canLook) {
    stareOrLook();
  }
});

body.addEventListener('mousemove', function (e) {
  rotate(document.querySelector('.left-eye'), e);
  rotate(document.querySelector('.right-eye'), e);
}, false);

function stareOrLook() {
  if (stare) {
    for (var eye of document.querySelectorAll('.eye, .eyes')) {
      eye.classList.remove('stare');
      eye.classList.add('look');
    }
  } else {
    for (var eye of document.querySelectorAll('.eye, .eyes')) {
      eye.classList.add('stare');
      eye.classList.remove('look');
    }
  }
  stare = !stare;
}

function rotate(eyes, e) {
  if (stare) {
    stareOrLook();
  }
  var mouseX = (eyes.getBoundingClientRect().left);
  var mouseY = (eyes.getBoundingClientRect().top);
  var radianDegrees = Math.atan2(e.pageX - mouseX, e.pageY - mouseY);
  var rotationDegrees = (radianDegrees * (180 / Math.PI) * -1) + 180;
  eyes.style.transform = `rotate(${rotationDegrees}deg)`
  canLook = true;
  clearInterval(interval);
  interval = setInterval(function() {
    if (!stare) {
      stareOrLook();
    }
  }, 2000);
}

var interval = setInterval(function() {
  if (!stare) {
    stareOrLook();
  }
}, 2000);

setTimeout(function() {
  document.querySelector('.mouth.open').classList.add('hidden');
  document.querySelector('.mouth.closed').classList.remove('hidden');
}, 2000);
