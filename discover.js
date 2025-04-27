document.addEventListener('DOMContentLoaded', function() {
    var tinderContainer = document.querySelector('.tinder');
    var allCards = document.querySelectorAll('.tinder--card');
    var nope = document.querySelector('.button-pass');
    var love = document.querySelector('.button-like');

    function initCards() {
        var newCards = document.querySelectorAll('.tinder--card:not(.removed)');

        newCards.forEach(function(card, index) {
            card.style.zIndex = allCards.length - index;
            card.style.transform = 'scale(' + (20 - index) / 20 + ') translateY(-' + 30 * index + 'px)';
            card.style.opacity = (10 - index) / 10;
        });

        if (newCards.length === 0) {
            showNoMoreCards();
        }
    }

    function showNoMoreCards() {
        const container = document.querySelector('.tinder');
        container.innerHTML = `
            <div style="text-align: center; padding: 2rem;">
                <h2>No More Profiles</h2>
                <p>Check back later for more potential matches!</p>
                <a href="/dashboard" class="btn btn-primary">Back to Dashboard</a>
            </div>
        `;
    }

    initCards();

    allCards.forEach(function(el) {
        var hammertime = new Hammer(el);

        hammertime.get('pan').set({ direction: Hammer.DIRECTION_ALL });

        hammertime.on('pan', function(event) {
            if (el.classList.contains('removed')) return;
            el.classList.add('moving');

            if (event.deltaX === 0) return;
            if (event.center.x === 0 && event.center.y === 0) return;

            tinderContainer.classList.toggle('tinder_love', event.deltaX > 0);
            tinderContainer.classList.toggle('tinder_nope', event.deltaX < 0);

            var xMulti = event.deltaX * 0.03;
            var yMulti = event.deltaY / 80;
            var rotate = xMulti * yMulti;

            el.style.transform = 'translate(' + event.deltaX + 'px, ' + event.deltaY + 'px) rotate(' + rotate + 'deg)';

            // Update stamps
            const likeStamp = el.querySelector('.stamp.like');
            const nopeStamp = el.querySelector('.stamp.nope');
            
            if (event.deltaX > 0) {
                likeStamp.style.opacity = Math.min(event.deltaX / 100, 1);
                nopeStamp.style.opacity = 0;
            } else {
                nopeStamp.style.opacity = Math.min(Math.abs(event.deltaX) / 100, 1);
                likeStamp.style.opacity = 0;
            }
        });

        hammertime.on('panend', function(event) {
            el.classList.remove('moving');
            tinderContainer.classList.remove('tinder_love');
            tinderContainer.classList.remove('tinder_nope');

            var moveOutWidth = document.body.clientWidth;
            var keep = Math.abs(event.deltaX) < 80 || Math.abs(event.velocityX) < 0.5;

            if (keep) {
                el.style.transform = '';
                resetStamps(el);
            } else {
                var endX = Math.max(Math.abs(event.velocityX) * moveOutWidth, moveOutWidth);
                var toX = event.deltaX > 0 ? endX : -endX;
                var endY = Math.abs(event.velocityY) * moveOutWidth;
                var toY = event.deltaY > 0 ? endY : -endY;
                var xMulti = event.deltaX * 0.03;
                var yMulti = event.deltaY / 80;
                var rotate = xMulti * yMulti;

                el.style.transform = 'translate(' + toX + 'px, ' + (toY + event.deltaY) + 'px) rotate(' + rotate + 'deg)';
                el.classList.add('removed');

                // Handle like/pass based on swipe direction
                if (event.deltaX > 0) {
                    handleLike(el);
                } else {
                    handlePass(el);
                }

                initCards();
            }
        });
    });

    function resetStamps(card) {
        const likeStamp = card.querySelector('.stamp.like');
        const nopeStamp = card.querySelector('.stamp.nope');
        likeStamp.style.opacity = 0;
        nopeStamp.style.opacity = 0;
    }

    async function handleLike(card) {
        const userId = card.dataset.userId;
        try {
            const response = await fetch(`/like/${userId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            
            const data = await response.json();
            
            // Show match notification with phone number for Mock3
            if (data.status === 'matched') {
                const matchedUser = {
                    username: card.querySelector('.name').textContent,
                    phone: card.dataset.phone || '+1 (555) 123-4567' // Default phone if not set
                };
                showMatchNotification(matchedUser);
            }
            
            // Remove the card
            card.classList.add('removed');
            setTimeout(() => {
                card.remove();
                initCards();
            }, 300);
            
        } catch (error) {
            console.error('Error:', error);
            card.style.transform = '';
            card.classList.remove('removed');
        }
    }

    async function handlePass(card) {
        const userId = card.dataset.userId;
        try {
            const response = await fetch(`/pass/${userId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            
            // Remove the card
            card.classList.add('removed');
            setTimeout(() => {
                card.remove();
                initCards();
            }, 300);
            
        } catch (error) {
            console.error('Error:', error);
            // Reset card position on error
            card.style.transform = 'translate(0px, 0px) rotate(0deg)';
            card.classList.remove('removed');
        }
    }

    function createButtonListener(love) {
        return function(event) {
            var cards = document.querySelectorAll('.tinder--card:not(.removed)');
            var moveOutWidth = document.body.clientWidth * 1.5;

            if (!cards.length) return;

            var card = cards[0];

            card.classList.add('removed');

            if (love) {
                card.style.transform = 'translate(' + moveOutWidth + 'px, -100px) rotate(-30deg)';
                handleLike(card);
            } else {
                card.style.transform = 'translate(-' + moveOutWidth + 'px, -100px) rotate(30deg)';
                handlePass(card);
            }

            initCards();
        };
    }

    nope.addEventListener('click', createButtonListener(false));
    love.addEventListener('click', createButtonListener(true));

    function showMatchNotification(matchedUser) {
        // Create and show a match notification
        const notification = document.createElement('div');
        notification.className = 'match-notification';
        notification.innerHTML = `
            <div class="match-content">
                <h2>It's a Match! 🎉</h2>
                <p>You've made a new connection with ${matchedUser.username}!</p>
                <p>Phone: ${matchedUser.phone}</p>
                <div class="match-actions">
                    <button onclick="this.parentElement.parentElement.parentElement.remove()" class="btn btn-secondary">Keep Browsing</button>
                    <a href="/matches" class="btn btn-primary">View Matches</a>
                </div>
            </div>
        `;
        document.body.appendChild(notification);
        
        // Add match notification styles if not already in your CSS
        const style = document.createElement('style');
        style.textContent = `
            .match-notification {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0,0,0,0.8);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 1000;
                animation: fadeIn 0.3s ease;
            }
            
            .match-content {
                background: white;
                padding: 2rem;
                border-radius: 20px;
                text-align: center;
                animation: scaleIn 0.3s ease;
            }
            
            .match-actions {
                margin-top: 1rem;
                display: flex;
                gap: 1rem;
                justify-content: center;
            }
            
            @keyframes fadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }
            
            @keyframes scaleIn {
                from { transform: scale(0.8); }
                to { transform: scale(1); }
            }
        `;
        document.head.appendChild(style);
    }
});