// Instance the tour
var tour = new Tour({
    steps: [
        {
            orphan: true,
            title: "Welcome to BigBox",
            content: "Hi! First time to BigBox? Let us show you what awesome features we have."
        },
        {
            element: "#listr-table",
            title: "File list",
            placement: "bottom",
            content: "You can see files on all of your cloud drives here, in one single list."
        },
        {
            element: "#files-left-nav",
            title: "Cloud filter and colors",
            content: "Each cloud is represented by a color, so you'll know which one a file belongs to."
        },
        {
            element: "#upload-left-button",
            title: "Upload and new folder",
            placement: "bottom",
            content: "Just like what you'd want to do on any other clouds."
        },
        {
            element: "#nav-pages",
            title: "Check out other pages",
            placement: "bottom",
            content: "Manage your cloud accounts in Clouds, and see your shared files in Sharing. We'll now take you to Clouds page to start with.",
            backdrop: false
        },
        {
            path: "/clouds?tour=1",
            element: "#link-cloud-button",
            title: "Manage cloud accounts",
            content: "Link your all cloud accounts now to start using!",
            reflex: true
        }
    ],
    backdrop: true
});

// Initialize the tour
tour.init();

// Start the tour
tour.start();
