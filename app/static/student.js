// ============================
// GET HTML ELEMENTS
// ============================

const video = document.getElementById('video');

const canvas = document.getElementById('canvas');

const captureButton = document.getElementById('capture');

const capturedImageInput = document.getElementById('captured_image');

const preview = document.getElementById('preview');


// ============================
// OPEN WEBCAM
// ============================

navigator.mediaDevices.getUserMedia({
    video: true
})

.then(function(stream){

    // SHOW LIVE CAMERA

    video.srcObject = stream;

})

.catch(function(error){

    alert('Unable to access webcam');

    console.log(error);

});


// ============================
// CAPTURE PHOTO
// ============================

captureButton.addEventListener('click', function(){

    // GET CANVAS CONTEXT

    const context = canvas.getContext('2d');

    // CAPTURE CURRENT VIDEO FRAME

    context.drawImage(video, 0, 0, 400, 300);

    // CONVERT IMAGE TO BASE64

    const imageData = canvas.toDataURL('image/png');

    // STORE INSIDE HIDDEN INPUT

    capturedImageInput.value = imageData;

    // SHOW IMAGE PREVIEW

    preview.src = imageData;

    preview.classList.remove('d-none');

    alert('Photo Captured Successfully');

});