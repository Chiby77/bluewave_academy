document.getElementById('contactForm').addEventListener('submit', async function(e) {
    e.preventDefault();
   
    const formData = new FormData(this);
    const messageDiv = document.getElementById('formMessage');
    const submitButton = this.querySelector('.submit-button');
   
    submitButton.disabled = true;
    submitButton.textContent = 'Sending...';
   
    try {
        const response = await fetch(this.action, {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': formData.get('csrfmiddlewaretoken')
            }
        });
       
        const data = await response.json();
       
        if (data.success) {
            messageDiv.textContent = 'Message sent successfully! We\'ll get back to you soon.';
            messageDiv.className = 'form-message success';
            this.reset();
        } else {
            messageDiv.textContent = data.error || 'Something went wrong. Please try again.';
            messageDiv.className = 'form-message error';
        }
       
    } catch (error) {
        console.error('Error:', error);
        messageDiv.textContent = 'Network error. Please check your connection and try again.';
        messageDiv.className = 'form-message error';
    }
   
    messageDiv.style.display = 'block';
    submitButton.disabled = false;
    submitButton.textContent = 'Send Message';
   
    // Hide message after 5 seconds
    setTimeout(() => {
        messageDiv.style.display = 'none';
    }, 5000);
});