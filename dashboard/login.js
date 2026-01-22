/**
 * Login Page Logic - OTP Authentication
 */

const API_BASE = '';  // Same origin

// State
let codeExpiresAt = null;
let timerInterval = null;

// ==================== DOM Elements ====================

const stepRequest = document.getElementById('step-request');
const stepVerify = document.getElementById('step-verify');
const step1Indicator = document.getElementById('step1');
const step2Indicator = document.getElementById('step2');
const btnRequestCode = document.getElementById('btn-request-code');
const btnVerify = document.getElementById('btn-verify');
const btnResend = document.getElementById('btn-resend');
const otpInput = document.getElementById('otp-input');
const messageRequest = document.getElementById('message-request');
const messageVerify = document.getElementById('message-verify');
const timerValue = document.getElementById('timer-value');
const resendTimer = document.getElementById('resend-timer');

// ==================== Check Auth Status ====================

async function checkExistingToken() {
    const token = localStorage.getItem('auth_token');
    
    try {
        const response = await fetch(`${API_BASE}/api/auth/validate`, {
            headers: token ? { 'Authorization': `Bearer ${token}` } : {}
        });
        const data = await response.json();
        
        // If auth is disabled (message contains 'disabled'), go to dashboard
        if (data.message && data.message.includes('disabled')) {
            console.log('Auth disabled - redirecting to dashboard');
            window.location.href = '/';
            return;
        }
        
        // If token is valid, go to dashboard
        if (data.valid) {
            window.location.href = '/';
            return;
        }
    } catch (e) {
        // Token invalid, stay on login page
        localStorage.removeItem('auth_token');
    }
}

// ==================== Request Code ====================

async function requestCode() {
    setLoading(btnRequestCode, true, '📧 Sending...');
    hideMessage(messageRequest);
    hideMessage(messageVerify);
    
    try {
        const response = await fetch(`${API_BASE}/api/auth/request-code`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const data = await response.json();
        
        if (data.success) {
            showMessage(messageRequest, data.message, 'success');
            
            // Move to step 2 after short delay
            setTimeout(() => {
                showStep2();
                startTimer(data.expires_in || 600);
            }, 1000);
        } else {
            showMessage(messageRequest, data.error || 'Failed to send code', 'error');
        }
    } catch (error) {
        showMessage(messageRequest, 'Network error. Please try again.', 'error');
    } finally {
        setLoading(btnRequestCode, false, '📧 Send Auth Code');
    }
}

// ==================== Verify Code ====================

async function verifyCode() {
    const code = otpInput.value.trim();
    
    if (code.length !== 8 || !/^\d+$/.test(code)) {
        showMessage(messageVerify, 'Please enter a valid 8-digit code', 'error');
        return;
    }
    
    setLoading(btnVerify, true, '🔓 Verifying...');
    hideMessage(messageVerify);
    
    try {
        const response = await fetch(`${API_BASE}/api/auth/verify-code`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code })
        });
        
        const data = await response.json();
        
        if (data.success && data.token) {
            // Store token
            localStorage.setItem('auth_token', data.token);
            
            showMessage(messageVerify, '✅ Authentication successful! Redirecting...', 'success');
            
            // Stop timer
            if (timerInterval) clearInterval(timerInterval);
            
            // Redirect to dashboard
            setTimeout(() => {
                window.location.href = '/';
            }, 1000);
        } else {
            showMessage(messageVerify, data.error || 'Invalid code', 'error');
            otpInput.value = '';
            otpInput.focus();
        }
    } catch (error) {
        showMessage(messageVerify, 'Network error. Please try again.', 'error');
    } finally {
        setLoading(btnVerify, false, '🔓 Verify & Login');
    }
}

// ==================== UI Helpers ====================

function showStep2() {
    stepRequest.classList.add('hidden');
    stepVerify.classList.remove('hidden');
    step1Indicator.classList.remove('active');
    step1Indicator.classList.add('completed');
    step1Indicator.textContent = '✓';
    step2Indicator.classList.add('active');
    
    // Focus OTP input
    setTimeout(() => otpInput.focus(), 100);
}

function showStep1() {
    stepVerify.classList.add('hidden');
    stepRequest.classList.remove('hidden');
    step1Indicator.classList.add('active');
    step1Indicator.classList.remove('completed');
    step1Indicator.textContent = '1';
    step2Indicator.classList.remove('active');
    
    // Clear OTP
    otpInput.value = '';
}

function showMessage(element, message, type) {
    element.textContent = message;
    element.className = `message ${type}`;
}

function hideMessage(element) {
    element.className = 'message';
    element.textContent = '';
}

function setLoading(button, loading, text) {
    button.disabled = loading;
    if (loading) {
        button.innerHTML = `<div class="spinner"></div> ${text}`;
    } else {
        button.innerHTML = text;
    }
}

function startTimer(seconds) {
    codeExpiresAt = Date.now() + (seconds * 1000);
    btnResend.classList.add('hidden');
    resendTimer.classList.remove('hidden');
    
    if (timerInterval) clearInterval(timerInterval);
    
    updateTimer();
    timerInterval = setInterval(updateTimer, 1000);
}

function updateTimer() {
    const remaining = Math.max(0, codeExpiresAt - Date.now());
    const minutes = Math.floor(remaining / 60000);
    const secs = Math.floor((remaining % 60000) / 1000);
    
    timerValue.textContent = `${minutes}:${secs.toString().padStart(2, '0')}`;
    
    if (remaining <= 0) {
        clearInterval(timerInterval);
        resendTimer.classList.add('hidden');
        btnResend.classList.remove('hidden');
        showMessage(messageVerify, 'Code expired. Please request a new one.', 'error');
    }
}

// ==================== Event Listeners ====================

// Auto-format OTP input (digits only)
otpInput.addEventListener('input', (e) => {
    e.target.value = e.target.value.replace(/\D/g, '').slice(0, 8);
    
    // Auto-submit when 8 digits entered
    if (e.target.value.length === 8) {
        verifyCode();
    }
});

// Enter key to submit
otpInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && otpInput.value.length === 8) {
        verifyCode();
    }
});

// ==================== Initialize ====================

document.addEventListener('DOMContentLoaded', () => {
    checkExistingToken();
});
