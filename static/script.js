const typingForm = document.querySelector(".typing-form");
const chatContainer = document.querySelector(".chat-list");
// const suggestions = document.querySelectorAll(".suggestion");
const toggleThemeButton = document.querySelector("#theme-toggle-button");
const deleteChatButton = document.querySelector("#delete-chat-button");
// Call this function when the page loads
const projectsGrid = document.querySelector('.projects-grid');


// State variables
let userMessage = null;
let isResponseGenerating = false;

// A simple auto-scroll function that scrolls the last message into view.
function scrollChatToBottom() {
  const lastMessage = chatContainer.lastElementChild;
  if (lastMessage) {
    lastMessage.scrollIntoView({ behavior: "smooth", block: "end" });
  }
}

// Dynamically load the projectsData with this function
async function loadProjectsData() {
  try {
    const response = await fetch('/get-projects');
    const data = await response.json();
    console.log('Raw data from server:', data); // Add this debug log
    return data;
  } catch (error) {
    console.error('Error loading projects:', error);
    return [];
  }
}

// createProjectCards function to use the project data
async function createProjectCards() {
  console.log('Creating project cards...');
  if (!projectsGrid) {
    console.error('Projects grid container not found!');
    return;
  }

  try {
    const projectsData = await loadProjectsData();
    
    projectsData.forEach(project => {
      console.log('Project data:', project);
      
      const title = project['project title'] || 'Untitled Project';
      const tagline = project['tagline'] || 'No description available';
      const techTags = project['techTags'] || [];

      const card = document.createElement('div');
      card.className = 'project-card';
      
      const techTagsHTML = Array.isArray(techTags) 
        ? techTags.map(tag => `<span class="tech-tag">${tag}</span>`).join('')
        : '';
      
      card.innerHTML = `
        <div class="project-info">
          <h3 class="project-title">${title}</h3>
          <p class="project-tagline">${tagline}</p>
          <div class="tech-tags">
            ${techTagsHTML}
          </div>
        </div>
      `;
      
      card.addEventListener('click', () => {
        userMessage = `Tell me about the ${title} project`;
        handleOutgoingChat();
      });
      
      projectsGrid.appendChild(card);
    });
  } catch (error) {
    console.error('Error creating project cards:', error);
  }
}


// Load theme and chat data from local storage on page load
const loadDataFromLocalstorage = () => {
  const savedChats = localStorage.getItem("saved-chats");
  const isLightMode = (localStorage.getItem("themeColor") === "light_mode");

  // Apply the stored theme
  document.body.classList.toggle("light_mode", isLightMode);
  toggleThemeButton.innerText = isLightMode ? "dark_mode" : "light_mode";

  // Restore saved chats or clear the chat container
  chatContainer.innerHTML = savedChats || '';
  document.body.classList.toggle("hide-header", savedChats);


  scrollChatToBottom();
  // chatContainer.scrollTo(0, chatContainer.scrollHeight); // Scroll to the bottom
}


// Create a new message element and return it
const createMessageElement = (content, ...classes) => {
  const div = document.createElement("div");
  div.classList.add("message", ...classes);
  div.innerHTML = content;
  return div;
}

// Show full response text, image, and video preview after a 1-second delay
// const showResponseAfterDelay = (text, textElement, incomingMessageDiv, videoUrl, imageUrl) => {
//   setTimeout(() => {
//     textElement.innerHTML = `${text}<br><br>`; // Display full response text with some space
//     displayMediaPreview(videoUrl, imageUrl, textElement); // Show video and image preview
//     isResponseGenerating = false;
//     incomingMessageDiv.querySelector(".icon").classList.remove("hide");
//     localStorage.setItem("saved-chats", chatContainer.innerHTML); // Save chats to local storage

//     scrollChatToBottom();
//     // chatContainer.scrollTo(0, chatContainer.scrollHeight); // Scroll to the bottom
//   }, 1000);
// };


// Fetch response from the Flask backend based on user message
const generateAPIResponse = async (incomingMessageDiv) => {
  const textElement = incomingMessageDiv.querySelector(".text"); // Getting text element

  try {
    // Send a POST request to the Flask backend with the user's message
    const response = await fetch('/generate-response', {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: userMessage }),
    });

    const data = await response.json();
    if (!response.ok) throw new Error(data.error);

    // Determine if this is a project response or personal response
    const isProjectResponse = data["Project Title"] && data["Project Title"].trim() !== "";
    
    // Remove loading class before updating content
    incomingMessageDiv.classList.remove("loading");
    
    if (isProjectResponse) {
      // For project responses, create a special styled card
      incomingMessageDiv.innerHTML = createProjectResponseCard(data);
    } else {
      // For personal responses (about portfolio, skills, etc) - updated with consistent icon
      incomingMessageDiv.innerHTML = `
        <div class="message-content">
          <span class="avatar-icon material-symbols-rounded">smart_toy</span>
          <div class="personal-response">
            <p class="text">${data["Description"]}</p>
          </div>
        </div>
      `;
    }
    
    isResponseGenerating = false;
    localStorage.setItem("saved-chats", chatContainer.innerHTML); // Save chats to local storage
    scrollChatToBottom();

  } catch (error) { // Handle error
    isResponseGenerating = false;
    incomingMessageDiv.classList.remove("loading");
    incomingMessageDiv.innerHTML = `
      <div class="message-content">
        <span class="avatar-icon material-symbols-rounded error-icon">error</span>
        <div class="personal-response">
          <p class="text">${error.message}</p>
        </div>
      </div>
    `;
  }
};

// Create a stylized project response card
const createProjectResponseCard = (data) => {
  // Extract tech stack tags from description if available
  const techStackMatch = data["Description"].match(/<h3>Tech Stack.*?<\/h3>(.*?)(?=<h3>|$)/is);
  let techStackHTML = '';
  
  if (techStackMatch && techStackMatch[1]) {
    // Extract technology names from the tech stack section
    const techMatches = techStackMatch[1].match(/\b(Python|Flask|HTML|CSS|JavaScript|Bootstrap|AI|ML|NLP|TensorFlow|PyTorch|Keras|GPT|LLM|RAG|API|OPENAI|Gemini|Vector Embeddings| Vector database)\b/gi);
    
    if (techMatches) {
      const uniqueTechs = [...new Set(techMatches)]; // Remove duplicates
      techStackHTML = uniqueTechs.map(tech => `<span class="tech-tag">${tech}</span>`).join('');
    }
  }
  
  // Format the video if available
  let videoHTML = '';
  if (data["Video"] && data["Video"].trim() !== "") {
    const videoIdMatch = data["Video"].match(
      /(?:youtube\.com\/(?:[^\/]+\/[^\/]+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})/
    );
    
    if (videoIdMatch && videoIdMatch[1]) {
      const videoId = videoIdMatch[1];
      const embedUrl = `https://www.youtube.com/embed/${videoId}`;
      
      videoHTML = `
        <div class="media-preview">
          <iframe 
            src="${embedUrl}" 
            allowfullscreen>
          </iframe>
        </div>
      `;
    }
  }
  
  // Process the project description to make it more readable with collapsible sections
  const processedDescription = processProjectDescription(data["Description"]);
  
  // Create the response card HTML 
  return `
    <div class="message-content">
      <span class="avatar-icon material-symbols-rounded">smart_toy</span>
      <div class="project-response-card">
        <div class="project-response-header">
          <h3 class="project-response-title">
            <span class="project-icon material-symbols-rounded">rocket_launch</span>
            ${data["Project Title"]}
          </h3>
        </div>
        <div class="project-response-body">
          ${processedDescription}
          ${videoHTML}
        </div>
        ${techStackHTML ? 
          `<div class="project-response-footer">
            <div class="project-tech-tags">
              ${techStackHTML}
            </div>
          </div>` : ''}
      </div>
    </div>
  `;
};

// Helper function to process project description and make it more readable
const processProjectDescription = (description) => {
  if (!description) return '';
  
  // Check if description has h3 headers already
  if (description.includes('<h3>')) {
    // Find all h3 tags and their content
    const sections = description.split(/<h3>(.*?)<\/h3>/g);
    let result = '';
    
    if (sections.length > 1) {
      // First part might be intro text before any headers
      if (sections[0].trim()) {
        result += `<div class="project-intro">${sections[0]}</div>`;
      }
      
      // Process each section with a header
      for (let i = 1; i < sections.length; i += 2) {
        const headerText = sections[i];
        const content = sections[i + 1] || '';
        
        if (headerText && headerText.trim()) {
          // Create collapsible section with unique id
          const sectionId = `section-${i}-${Date.now()}`;
          result += `
            <div class="collapsible-section">
              <div class="section-header" onclick="toggleSection('${sectionId}')">
                <h3>${headerText}</h3>
                <span class="toggle-icon material-symbols-rounded">expand_more</span>
              </div>
              <div id="${sectionId}" class="section-content" style="display:none;">
                ${content}
              </div>
            </div>
          `;
        }
      }
    } else {
      // No h3 tags found or processing failed, return original
      return description;
    }
    
    return result;
  } else {
    // If no h3 tags, create a summarized version
    const summary = description.substring(0, 200) + (description.length > 200 ? '...' : '');
    const detailId = `detail-${Date.now()}`;
    
    return `
      <div class="project-summary">${summary}</div>
      <div class="show-more-container">
        <button class="show-more-btn" onclick="toggleDetail('${detailId}')">
          Show More <span class="material-symbols-rounded">expand_more</span>
        </button>
        <div id="${detailId}" class="project-detail" style="display: none;">
          ${description}
        </div>
      </div>
    `;
  }
};

// Show a loading animation while waiting for the API response
const showLoadingAnimation = () => {
  const html = `<div class="message-content">
                  <span class="avatar-icon material-symbols-rounded">smart_toy</span>
                  <div class="personal-response">
                    <div class="typing-dots">
                      <div class="dot"></div>
                      <div class="dot"></div>
                      <div class="dot"></div>
                    </div>
                  </div>
                </div>`;

  const incomingMessageDiv = createMessageElement(html, "incoming", "loading");
  chatContainer.appendChild(incomingMessageDiv);

  scrollChatToBottom();
  generateAPIResponse(incomingMessageDiv);
}

// Display video preview
// image parameter is commented out
// const displayMediaPreview = (videoUrl, imageUrls, textElement)
// const displayMediaPreview = (videoUrl, imageUrls, textElement) => {
//   // Extract YouTube video ID from different URL formats
//   const videoIdMatch = videoUrl.match(
//     /(?:youtube\.com\/(?:[^\/]+\/[^\/]+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})/
//   );

//   // Check if a valid video ID was found
//   if (!videoIdMatch || !videoIdMatch[1]) {
//     console.error("Invalid YouTube URL:", videoUrl);
//     return;
//   }

//   const videoId = videoIdMatch[1];
//   const embedUrl = `https://www.youtube.com/embed/${videoId}`;

//   // Create the media container element
//   const mediaContainer = document.createElement("div");
//   mediaContainer.classList.add("media-preview");

//   // Create the video iframe element
//   const videoElement = document.createElement("iframe");
//   videoElement.width = "460";
//   videoElement.height = "315";
//   videoElement.src = embedUrl;
//   videoElement.frameBorder = "0";
//   videoElement.allow = "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture";
//   videoElement.allowFullscreen = true;

//   // Append video element to the media container
//   mediaContainer.appendChild(videoElement);

//   // // Create a container for images
//   // const imagesContainer = document.createElement("div");
//   // imagesContainer.classList.add("images-container");

//   // // Create and append image elements to the images container
//   // imageUrls.forEach((imageUrl) => {
//   //   const imageElement = document.createElement("img");
//   //   imageElement.src = imageUrl;
//   //   imageElement.alt = "Project Image";
//   //   imageElement.style.width = "auto";
//   //   imageElement.style.height = "315px";
//   //   imageElement.style.maxWidth = "360px";
//   //   imageElement.style.objectFit = "contain";
//   //   imageElement.style.marginTop = "10px"; // Add space between images
//   //   imageElement.style.marginLeft = "10px";
//   //   imagesContainer.appendChild(imageElement);
//   // });

//   // // Append images container to the media container
//   // mediaContainer.appendChild(imagesContainer);

//   // Append media container to the text element
//   textElement.appendChild(mediaContainer);
// };


// Handle sending outgoing chat messages
const handleOutgoingChat = () => {
  userMessage = typingForm.querySelector(".typing-input").value.trim() || userMessage;
  if (!userMessage || isResponseGenerating) return; // Exit if there is no message or response is generating

  isResponseGenerating = true;

  // Consistent structure for outgoing messages - updated with more generic user icon
  const html = `<div class="message-content">
                  <span class="avatar-icon material-symbols-rounded">account_circle</span>
                  <div class="text-container">
                    <div class="user-query-bubble">
                      <p class="text"></p>
                    </div>
                  </div>
                </div>`;

  const outgoingMessageDiv = createMessageElement(html, "outgoing");
  outgoingMessageDiv.querySelector(".text").innerText = userMessage;
  chatContainer.appendChild(outgoingMessageDiv);

  typingForm.reset(); // Clear input field
  document.body.classList.add("hide-header");

  scrollChatToBottom();
  setTimeout(showLoadingAnimation, 500); // Show loading animation after a delay
}

// Toggle between light and dark themes
toggleThemeButton.addEventListener("click", () => {
  const isLightMode = document.body.classList.toggle("light_mode");
  localStorage.setItem("themeColor", isLightMode ? "light_mode" : "dark_mode");
  toggleThemeButton.innerText = isLightMode ? "dark_mode" : "light_mode";
});

// Delete all chats from local storage when button is clicked
deleteChatButton.addEventListener("click", () => {
  if (confirm("Are you sure you want to delete all the chats?")) {
    localStorage.removeItem("saved-chats");
    loadDataFromLocalstorage();
  }
  // to show initial greeting message and prompts again 
  showInitialChatGreeting();
});



// ********* Starter Msgs ************* 

// New loading animation function for starter messages
function showStarterLoadingAnimation() {
  // Create a new loading element with the typing dots
  const loadingHTML = `
    <div class="message-content">
      <span class="avatar-icon material-symbols-rounded">smart_toy</span>
      <div class="personal-response">
        <div class="typing-dots">
          <div class="dot"></div>
          <div class="dot"></div>
          <div class="dot"></div>
        </div>
      </div>
    </div>
  `;
  const loadingElement = createMessageElement(loadingHTML, "incoming", "loading");
  chatContainer.appendChild(loadingElement);
  scrollChatToBottom();
  return loadingElement; // Return this element so we can update or remove it later.
}

// Starter Messages Section with typing animation
const showInitialChatGreeting = async () => {
  // Create and append the greeting message with typing effect immediately
  const greetingMessage = createMessageElement(
    `<div class="message-content">
       <span class="avatar-icon material-symbols-rounded">smart_toy</span>
       <div class="personal-response greeting-container">
         <p class="typing-effect">Hi! I'm Anaiza. Would you like to hear more about me?</p>
       </div>
     </div>`, 
    "incoming"
  );
  chatContainer.appendChild(greetingMessage);
  scrollChatToBottom();

  // Wait for typing animation to complete (adjusted to match the new animation timing)
  await new Promise(resolve => setTimeout(resolve, 4000));

  // Create and append the starter messages container
  const startersMessage = createMessageElement(
    `<div class="message-content">
       <div class="chat-starters-container">
         <div class="conversation-starters">
           <button class="starter-btn" data-message="Who is Anaiza Tariq?">Who is Anaiza Tariq?</button>
           <button class="starter-btn" data-message="What drives your passion for AI and ML?">What drives your passion for AI and ML?</button>
           <button class="starter-btn" data-message="What are your key technical skills?">What are your key technical skills?</button>
           <button class="starter-btn" data-message="Tell me about your notable projects">Tell me about your notable projects</button>
           <button class="starter-btn" data-message="Which technologies do you work with?">Which technologies do you work with?</button>
           <button class="starter-btn" data-message="How do you apply AI in real-world solutions?">How do you apply AI in real-world solutions?</button>
         </div>
       </div>
     </div>`, 
    "incoming"
  );
  chatContainer.appendChild(startersMessage);
  scrollChatToBottom();
};

// Event delegation: attach one click listener on the document that will handle
// clicks on any element matching '.chat-starters-container .starter-btn'.
document.addEventListener('click', async (event) => {
  const target = event.target;
  if (target.matches('.chat-starters-container .starter-btn')) {
    const message = target.getAttribute('data-message');
    document.querySelector('.typing-input').value = message;
    
    // Append the user's outgoing message
    const outgoingMessage = createMessageElement(
      `<div class="message-content">
         <span class="avatar-icon material-symbols-rounded">account_circle</span>
         <div class="text-container">
           <div class="user-query-bubble">
             <p class="text">${message}</p>
           </div>
         </div>
       </div>`, 
      "outgoing"
    );
    chatContainer.appendChild(outgoingMessage);
    scrollChatToBottom();
    
    // Call the loading animation function with typing dots
    const loadingMessage = showStarterLoadingAnimation();
    
    // Fetch the response for the starter question from the backend
    try {
      const response = await fetch('/process-starter-question', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message })
      });
      const data = await response.json();
      
      // Replace the loading animation with the fetched response
      loadingMessage.classList.remove("loading");
      loadingMessage.innerHTML = `
        <div class="message-content">
          <span class="avatar-icon material-symbols-rounded">smart_toy</span>
          <div class="personal-response">
            <p class="text">${data.Description}</p>
          </div>
        </div>
      `;
      
      // Save chat to local storage
      localStorage.setItem("saved-chats", chatContainer.innerHTML);
    } catch (err) {
      console.error("Error fetching response:", err);
      loadingMessage.classList.remove("loading");
      loadingMessage.innerHTML = `
        <div class="message-content">
          <span class="avatar-icon material-symbols-rounded error-icon">error</span>
          <div class="personal-response">
            <p class="text">Sorry, an error occurred while processing your request.</p>
          </div>
        </div>
      `;
    }
    
    // Clear the input and scroll to the bottom once done
    document.querySelector('.typing-input').value = '';
    scrollChatToBottom();
  }
});


// Modify document ready event listener - consolidate
document.addEventListener('DOMContentLoaded', async () => {
  try {
    // Load data immediately without delay
    loadDataFromLocalstorage();
    // Create project cards immediately
    await createProjectCards();
    // Check if there are no saved chats, then show initial greeting immediately
    if (!localStorage.getItem("saved-chats")) {
      await showInitialChatGreeting();
    }
  } catch (error) {
    console.error('Error during initialization:', error);
  }
});


// // Set userMessage and handle outgoing chat when a suggestion is clicked
// suggestions.forEach(suggestion => {
//   suggestion.addEventListener("click", () => {
//     userMessage = suggestion.querySelector(".text").innerText;
//     handleOutgoingChat();
//   });
// });


// Prevent default form submission and handle outgoing chat
typingForm.addEventListener("submit", (e) => {
  e.preventDefault();
  handleOutgoingChat();
});

loadDataFromLocalstorage();

// Add these toggle functions to handle section expanding/collapsing
// Place it at the end of your script.js file
// These functions need to be in global scope to be callable from HTML

// Handle showing/hiding collapsible sections
function toggleSection(sectionId) {
  const section = document.getElementById(sectionId);
  const header = section.previousElementSibling;
  const icon = header.querySelector('.toggle-icon');
  
  // Check if section display is empty (initial state) or none
  if (section.style.display === '' || section.style.display === 'none') {
    // Show section with a small timeout to ensure smooth transition
    setTimeout(() => {
      section.style.display = 'block';
      icon.textContent = 'expand_less';
      icon.style.transform = 'rotate(180deg)';
    }, 10);
  } else {
    // Hide section
    section.style.display = 'none';
    icon.textContent = 'expand_more';
    icon.style.transform = 'rotate(0deg)';
  }
}

// Handle showing/hiding full project details(in-case when llm return respones without formating)
function toggleDetail(detailId) {
  const detail = document.getElementById(detailId);
  const button = detail.previousElementSibling;
  const icon = button.querySelector('.material-symbols-rounded');
  
  if (detail.style.display === 'none') {
    detail.style.display = 'block';
    button.innerHTML = 'Show Less <span class="material-symbols-rounded">expand_less</span>';
  } else {
    detail.style.display = 'none';
    button.innerHTML = 'Show More <span class="material-symbols-rounded">expand_more</span>';
  }
}

// Portfolio Navigation Script
// This script enables tabbed navigation in the left column of the portfolio.
// It listens for clicks on the navigation buttons and shows/hides the corresponding content sections.

document.addEventListener('DOMContentLoaded', () => {
  console.log("Portfolio nav script loaded");

  const navItems = document.querySelectorAll('.portfolio-nav .nav-item');
  const sections = document.querySelectorAll('.content-sections .section');

  if (navItems.length === 0) {
    console.error("No nav items found. Check your HTML markup.");
  } else {
    console.log(`Found ${navItems.length} nav items.`);
  }

  navItems.forEach(item => {
    item.addEventListener('click', () => {
      console.log(`Nav item clicked: ${item.textContent}`);
      // Remove active class from all nav items and hide all sections
      navItems.forEach(nav => nav.classList.remove('active'));
      sections.forEach(section => section.classList.remove('active'));

      // Add active class to the clicked nav item
      item.classList.add('active');

      // Get the corresponding section from the data-section attribute
      const sectionId = item.getAttribute('data-section');
      console.log(`Trying to activate section: ${sectionId}`);
      const targetSection = document.getElementById(sectionId);
      if (targetSection) {
        targetSection.classList.add('active');
        console.log(`Activated section: ${sectionId}`);
      } else {
        console.error(`Section with ID ${sectionId} not found.`);
      }
    });
  });
});



// Collapse contact section
document.addEventListener('DOMContentLoaded', function() {
  // Elements
  const contactPanel = document.querySelector('.contact-side-panel');
  const openButtons = document.querySelectorAll('.open-contact-panel');
  const closeButton = document.querySelector('.contact-panel-close');
  const messageField = document.getElementById('message');
  const charCount = document.getElementById('char-count');
  
   // Save the initial contact form HTML so we can restore it later.
   const contactFormContainer = document.querySelector('.contact-form');
   const originalContactFormHTML = contactFormContainer ? contactFormContainer.innerHTML : ''; 
  
  // Open contact panel
  openButtons.forEach(button => {
    button.addEventListener('click', () => {
      contactPanel.classList.add('active');
      document.body.classList.add('contact-panel-open');
    });
  });
  
  // Close contact panel
  closeButton.addEventListener('click', () => {
    contactPanel.classList.remove('active');
    document.body.classList.remove('contact-panel-open');
  });
  
  // Character counter for message
  if (messageField && charCount) {
    messageField.addEventListener('input', () => {
      const currentLength = messageField.value.length;
      charCount.textContent = currentLength;
      if (currentLength > 400) {
        charCount.classList.add('char-count-warning');
      } else {
        charCount.classList.remove('char-count-warning');
      }
    });
  }
   // Function to attach the contact form submission handler 
   function attachContactFormHandler(){
    const contactForm = document.querySelector('.contact-form');
    if (contactForm) {
      contactForm.addEventListener('submit', function(e) {
        e.preventDefault();

        // Disable the submit button immediately to prevent duplicate clicks.
        const submitButton = contactForm.querySelector('button[type="submit"]');
        if (submitButton) {
          submitButton.disabled = true;
        }
      
        // Gather form data into an object
        const formData = new FormData(contactForm);
        const dataObj = {
          name: formData.get('name'),
          email: formData.get('email'),
          subject: formData.get('subject'),
          message: formData.get('message')
        };
        fetch('/submit-contact', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(dataObj)
        })
        .then(response => response.json())
        .then(data => {
          let feedback = data.message || "Thank you for your message! I will respond shortly.";
          // Replace the form with a thank you message including two buttons:
          // one to close the panel and one to send another message.
          contactForm.innerHTML = `
            <div class="form-submitted">
              <span class="material-symbols-rounded success-icon">check_circle</span>
              <h3>Message Sent!</h3>
              <p>${feedback}</p>
              <button type="button" class="contact-panel-close-btn">Close</button>
              <button type="button" class="send-another-btn">Send Another Message</button>
            </div>
          `;
          // Close handler for the close button
          document.querySelector('.contact-panel-close-btn').addEventListener('click', () => {
            contactPanel.classList.remove('active');
            document.body.classList.remove('contact-panel-open');
          });
          // Handler for Send Another Message button: restore original form markup and reattach handlers.
          document.querySelector('.send-another-btn').addEventListener('click', () => {
            contactForm.innerHTML = originalContactFormHTML;
            attachContactFormHandler();
          });
        })
        .catch(error => {
          console.error('Error submitting contact message:', error);
          contactForm.innerHTML = `
            <div class="form-submitted">
              <span class="material-symbols-rounded error-icon">error</span>
              <h3>Error</h3>
              <p>There was an error sending your message. Please try again later.</p>
              <button type="button" class="contact-panel-close-btn">Close</button>
              <button type="button" class="send-another-btn">Send Another Message</button>
            </div>
          `;
          document.querySelector('.contact-panel-close-btn').addEventListener('click', () => {
            contactPanel.classList.remove('active');
            document.body.classList.remove('contact-panel-open');
          });
          document.querySelector('.send-another-btn').addEventListener('click', () => {
            contactForm.innerHTML = originalContactFormHTML;
            attachContactFormHandler();
          });
        });
      }, { once: true }); // Ensure the listener is automatically removed after first submission.
    }
  }
   // Attach the contact form handler initially
   if (contactFormContainer) {
    attachContactFormHandler();
  }
});
   

// Make the toggle functions available globally so they can be called from HTML
window.toggleSection = toggleSection;
window.toggleDetail = toggleDetail;