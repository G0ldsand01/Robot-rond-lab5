function onClickAvancer() {
    const moteurs = new Moteurs(false, false, true, false); // Forward
    postMoteurs(moteurs);
}

function onClickReculer() {
    const moteurs = new Moteurs(false, false, false, true); // Reverse
    postMoteurs(moteurs);
}

function onClickGauche() {
    const moteurs = new Moteurs(true, false, false, false); // Left
    postMoteurs(moteurs);
}

function onClickDroite() {
    const moteurs = new Moteurs(false, true, false, false); // Right
    postMoteurs(moteurs);
}

function onClickStop() {
  const moteurs = new Moteurs(false, false, false, false);
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
  fetch("http://192.168.4.163:5000/moteurs", {  // <-- updated IP here
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(moteurs),
  })
  .then(response => {
      if (response.ok) {
          console.log("Command sent successfully:", moteurs);
          document.getElementById("message").innerHTML = `Statut: ${JSON.stringify(moteurs)}`;
      } else {
          console.error("Error sending command:", response.status, response.statusText);
          document.getElementById("message").innerHTML = `Erreur: ${response.status} ${response.statusText} Voir la console pour plus de détails`;
      }
  })
  .catch(error => {
      console.error("Network error or invalid URL:", error);
      document.getElementById("message").innerHTML = `Erreur réseau: ${error} Voir la console pour plus de détails`;
  });
}
function postTrajectoire(trajectoire) {
  fetch("http://192.168.4.163:5000/trajectoire", {  // <-- updated IP here
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(trajectoire),
  })
  .then(response => {
      if (response.ok) {
          console.log("Trajectoire sent successfully:", trajectoire);
      } else {
          console.error("Error sending trajectoire:", response.status, response.statusText);
      }
  })
  .catch(error => {
      console.error("Network error or invalid URL:", error);
  });
}





// Handle OpenCV toggle
function onToggleOpenCv() {
  const openCvSwitch = document.getElementById("openCvSwitch");
  const liveCamera = document.getElementsByClassName("live-camera")[0];
  
  if (!openCvSwitch) {
    console.error("Element with ID 'openCvSwitch' not found.");
    return;
  }
  
  if (!liveCamera) {
    console.error("Element with class 'live-camera' not found.");
    return;
  }
  
  if (openCvSwitch.checked) {
    liveCamera.style.display = "block";
  } else {
    liveCamera.style.display = "none";
  }
}
class Trajectoire {
  constructor(...steps) {
    // If steps are simple strings, convert them to objects with a default duration
    this.steps = steps.map(step => {
      if (typeof step === 'string') {
        return { action: step, duration: 500 }; // Default 500ms duration
      }
      return step;
    });
  }
}

// Usage example with mixed format:
function onClickTrajet1() {
  const trajectoire = new Trajectoire(
    "enAvant", 
    {action: "Avant", duration: 1000},  // Move forward for 1 second
    "enAvant", 
    { action: "Droite", duration: 1000 },  // Turn right for 1 second
    "enAvant", 
    "enAvant"
  );
  postTrajectoire(trajectoire);
}

function onClickTrajet2() {
  const trajectoire = new Trajectoire(
    "enAvant", 
    "enAvant", 
    { action: "Gauche", duration: 1000 },  // Turn left for 1 second
    "enArriere", 
    "enArriere"
  );
  postTrajectoire(trajectoire);
}

function onClickTrajet3() {
  const trajectoire = new Trajectoire(
    "enAvant", 
    "enAvant", 
    {
      action: "Droite", 
      duration: 1000  // Turn right for 1 second
    },  
    "enAvant",
    "enAvant",
    { action: "Gauche", duration: 1000 },  // Turn left for 1 second
    "enAvant",
    "enAvant",
    { action: "Gauche", duration: 1000 },  // Turn left for 1 second
  );
  postTrajectoire(trajectoire);
}