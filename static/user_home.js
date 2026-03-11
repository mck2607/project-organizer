// Mobile menu toggle
function toggleMobileMenu() {
    const mobileNav = document.getElementById('mobileNav');
    mobileNav.classList.toggle('active');
}

// Close mobile menu when clicking outside
document.addEventListener('click', function(event) {
    const mobileNav = document.getElementById('mobileNav');
    const menuBtn = document.querySelector('.mobile-menu-btn');

    if (!mobileNav.contains(event.target) && !menuBtn.contains(event.target)) {
        mobileNav.classList.remove('active');
    }
});

// Wait for DOM to load
document.addEventListener('DOMContentLoaded', function() {
    // Chart.js default configuration
    Chart.defaults.backgroundColor = 'rgba(139, 92, 246, 0.1)';
    Chart.defaults.borderColor = '#8b5cf6';
    Chart.defaults.color = '#a1a1aa';

    // Follower Growth Chart
    const growthCtx = document.getElementById('growthChart').getContext('2d');
    const growthChart = new Chart(growthCtx, {
        type: 'line',
        data: {
            labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
            datasets: [{
                label: 'Followers (in K)',
                data: [120, 125, 130, 132, 138, 142, 148, 155, 162, 170, 177, 184.3],
                borderColor: '#8b5cf6',
                backgroundColor: 'rgba(139, 92, 246, 0.1)',
                borderWidth: 3,
                fill: true,
                tension: 0.4,
                pointBackgroundColor: '#8b5cf6',
                pointBorderColor: '#ffffff',
                pointBorderWidth: 2,
                pointRadius: 4,
                pointHoverRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            interaction: {
                intersect: false,
                mode: 'index'
            },
            scales: {
                y: {
                    beginAtZero: false,
                    grid: {
                        color: 'rgba(161, 161, 170, 0.1)',
                        borderColor: '#27272a'
                    },
                    ticks: {
                        color: '#71717a',
                        font: {
                            size: 12
                        }
                    },
                    border: {
                        color: '#27272a'
                    }
                },
                x: {
                    grid: {
                        color: 'rgba(161, 161, 170, 0.1)',
                        borderColor: '#27272a'
                    },
                    ticks: {
                        color: '#71717a',
                        font: {
                            size: 12
                        }
                    },
                    border: {
                        color: '#27272a'
                    }
                }
            }
        }
    });

    // Engagement Metrics Chart
    const engagementCtx = document.getElementById('engagementChart').getContext('2d');
    const engagementChart = new Chart(engagementCtx, {
        type: 'bar',
        data: {
            labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
            datasets: [{
                label: 'Engagement Rate (%)',
                data: [5.2, 5.5, 5.8, 6.2, 6.5, 6.7, 7.0, 7.3, 7.6, 7.9, 8.0, 8.2],
                backgroundColor: 'rgba(236, 72, 153, 0.8)',
                borderColor: '#ec4899',
                borderWidth: 1,
                borderRadius: 4,
                borderSkipped: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            interaction: {
                intersect: false,
                mode: 'index'
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(161, 161, 170, 0.1)',
                        borderColor: '#27272a'
                    },
                    ticks: {
                        color: '#71717a',
                        font: {
                            size: 12
                        }
                    },
                    border: {
                        color: '#27272a'
                    }
                },
                x: {
                    grid: {
                        color: 'rgba(161, 161, 170, 0.1)',
                        borderColor: '#27272a'
                    },
                    ticks: {
                        color: '#71717a',
                        font: {
                            size: 12
                        }
                    },
                    border: {
                        color: '#27272a'
                    }
                }
            }
        }
    });

    // Animate progress bars
    function animateProgressBars() {
        const progressBars = document.querySelectorAll('.progress-fill');
        progressBars.forEach(bar => {
            const width = bar.style.width;
            bar.style.width = '0%';
            setTimeout(() => {
                bar.style.width = width;
            }, 100);
        });
    }

    // Trigger progress bar animation
    animateProgressBars();

    // Add smooth scroll behavior
    document.documentElement.style.scrollBehavior = 'smooth';

    // Add loading animation for stat cards
    const statCards = document.querySelectorAll('.stat-card');
    statCards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        setTimeout(() => {
            card.style.transition = 'all 0.5s ease';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, index * 100);
    });
});