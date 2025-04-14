function onClickAvancer() {
    let moteurs = new Moteurs(false, false, true, false); // Forward
    postMoteurs(moteurs);
}

function onClickReculer() {
    let moteurs = new Moteurs(false, false, false, true); // Reverse
    postMoteurs(moteurs);
}

function onClickGauche() {
    let moteurs = new Moteurs(true, false, false, false); // Left
    postMoteurs(moteurs);
}

function onClickDroite() {
    let moteurs = new Moteurs(false, true, false, false); // Right
    postMoteurs(moteurs);
}

function onClickStop() {
  let moteurs = new Moteurs(false, false, false, false);
  postMoteurs(moteurs);
}

class Moteurs {
  constructor(
    isLeftPressed,
    isRightPressed,
    isForwardPressed,
    isReversePressed
  ) {
    this.isLeftPressed = isLeftPressed || false;
    this.isRightPressed = isRightPressed || false;
    this.isForwardPressed = isForwardPressed || false;
    this.isReversePressed = isReversePressed || false;
  }
}

function postMoteurs(moteurs) {
    fetch("http://192.168.4.163:5000/moteurs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(moteurs),
    })
    .then(response => {
        if (response.ok) {
            console.log("Command sent successfully");
        } else {
            console.error("Error sending command:", response.status, response.statusText);
        }
    })
    .catch(error => {
        console.error("Network error or invalid URL:", error);
    });
}

// Handle OpenCV toggle
function onToggleOpenCv() {
  const openCvSwitch = document.getElementById("openCvSwitch");
  if (openCvSwitch.checked) {
    document.getElementsByClassName("live-camera")[0].style.display =
      "block";
  } else {
    document.getElementsByClassName("live-camera")[0].style.display =
      "none";
  }
}