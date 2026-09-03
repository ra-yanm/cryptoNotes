document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-dismiss="flash"]').forEach(button => {
        button.addEventListener('click', () => button.parentElement.remove());
    });

    document.querySelectorAll('.flash-message').forEach(message => {
        setTimeout(() => message.remove(), 3000);
    });

    document.querySelectorAll('[data-toggle]').forEach(button => {
        button.addEventListener('click', () => {
            const target = document.getElementById(button.dataset.toggle);
            if (target) target.style.display = target.style.display === 'none' ? 'block' : 'none';
        });
    });

    const profileEditor = document.getElementById('profile-editor');
    if (profileEditor) {
        document.querySelectorAll('[data-profile-action="open"]').forEach(button => {
            button.addEventListener('click', () => {
                profileEditor.hidden = false;
                document.getElementById('personal_phn')?.focus();
            });
        });
        document.querySelectorAll('[data-profile-action="close"]').forEach(button => {
            button.addEventListener('click', () => { profileEditor.hidden = true; });
        });
        document.addEventListener('keydown', event => {
            if (event.key === 'Escape') profileEditor.hidden = true;
        });
    }
});