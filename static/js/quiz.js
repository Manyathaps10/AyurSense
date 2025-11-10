console.log("Quiz JS Loaded!");

document.addEventListener("DOMContentLoaded", () => {

  // ===== Developer Test Mode =====
  const developerMode = true;  // true = bypass login for testing
  if (developerMode && !localStorage.getItem("loggedIn")) {
      localStorage.setItem("loggedIn", "testuser@example.com");
  }

  const quizContainer = document.getElementById("quiz-container");

  const quiz = [
    { question: "Which dosha is related to fire?", options: ["Vata","Pitta","Kapha","All of these"], answer: "Pitta" },
    { question: "What is Ayurveda primarily based on?", options: ["Herbal medicine","Yoga","Dance","Meditation"], answer: "Herbal medicine" },
    { question: "Which element is dominant in Kapha dosha?", options: ["Air & Space","Fire & Water","Water & Earth","All Elements"], answer: "Water & Earth" }
  ];

  let currentQuestion = 0;
  let score = 0;

  const questionEl = document.getElementById("question");
  const optionsEl = document.querySelectorAll(".option-btn");
  const nextBtn = document.getElementById("next-btn");
  const scoreEl = document.getElementById("score");

  function loadQuestion() {
    const q = quiz[currentQuestion];
    questionEl.textContent = q.question;
    optionsEl.forEach((btn, i) => {
      btn.textContent = q.options[i];
      btn.disabled = false;
      btn.classList.remove("btn-success","btn-danger");
      btn.onclick = () => checkAnswer(btn, q.answer);
    });
  }

  function checkAnswer(btn, correctAnswer) {
    if(btn.textContent === correctAnswer){
      btn.classList.add("btn-success");
      score++;
    } else {
      btn.classList.add("btn-danger");
      optionsEl.forEach(b => {
        if(b.textContent === correctAnswer) b.classList.add("btn-success");
      });
    }
    optionsEl.forEach(b => b.disabled = true);
  }

  nextBtn.onclick = () => {
    currentQuestion++;
    if(currentQuestion < quiz.length){
      loadQuestion();
    } else {
      showScore();
    }
  }

  function showScore() {
    questionEl.textContent = "Quiz Completed!";
    document.querySelector(".options").style.display = "none";
    nextBtn.style.display = "none";
    scoreEl.textContent = `Your Score: ${score} / ${quiz.length}`;
  }

// ===== Check login =====
const checkLoginAndLoad = () => {
  if(localStorage.getItem("loggedIn")){
    loadQuestion();
  } else {
    quizContainer.innerHTML = `
      <h3 class="text-danger">Please login first to access the quiz!</h3>
      <a href="/login" class="btn btn-success mt-3">Login Now</a>
    `;
  }
};

// ✅ Give the browser a short delay so localStorage is guaranteed ready
setTimeout(checkLoginAndLoad, 100);


});
