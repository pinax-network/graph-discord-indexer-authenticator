// main.js

let web3;
let userAccount;
const messageTemplate = 'Please sign this message to verify your wallet address: ';
const urlParams = new URLSearchParams(window.location.search);
const token = urlParams.get('token');

if (!token) {
    console.error('Verification token is missing from the URL.');
    alert('Verification token is missing from the URL.');
}

const url = import.meta.env.VITE_URL;

if (!url) {
    console.error('URL is not set. Please check your .env file.');
    alert('URL is not configured. Please contact support.');
}

const port = import.meta.env.VITE_PORT;

if (!port) {
  console.error('PORT is not set. Please check your .env file.');
  alert('PORT is not configured. Please contact support.');
}

document.getElementById('connectWallet').addEventListener('click', async () => {
    if (typeof window.ethereum !== 'undefined') {
        web3 = new Web3(window.ethereum);
        try {
            const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
            userAccount = accounts[0];
            document.getElementById('walletAddress').innerText = `Connected wallet address:\n${userAccount}`;
            document.getElementById('signMessage').disabled = false;

            const message = messageTemplate + userAccount;
            const messageContainer = document.createElement('div');
            messageContainer.className = 'message';
            messageContainer.innerText = message;
            document.getElementById('messageContainer').appendChild(messageContainer);
        } catch (error) {
            console.error('User denied account access');
        }
    } else {
        console.error('No Ethereum provider found. Install MetaMask');
        alert('No Ethereum provider found. Please install MetaMask.');
    }
});

document.getElementById('signMessage').addEventListener('click', async () => {
    try {
        const message = messageTemplate + userAccount;
        const signature = await web3.eth.personal.sign(message, userAccount, '');
        const signatureContainer = document.createElement('div');
        signatureContainer.className = 'signature';
        signatureContainer.innerText = `Signature:\n${signature}`;
        document.getElementById('signatureContainer').appendChild(signatureContainer);

        const response = await fetch(`${url}:${port}/verify`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                token: token,
                wallet_address: userAccount,
                signature: signature
            })
        });

        const result = await response.json();
        const alertContainer = document.getElementById('alertContainer');
        alertContainer.innerHTML = '';

        if (response.ok) {
            const alert = document.createElement('div');
            alert.className = 'alert alert-success';
            alert.innerText = 'Verification successful!';
            alertContainer.appendChild(alert);
        } else {
            const alert = document.createElement('div');
            alert.className = 'alert alert-error';
            alert.innerText = 'Verification failed: ' + result.error;
            alertContainer.appendChild(alert);
        }
    } catch (error) {
        console.error('Error signing message:', error);
    }
});
