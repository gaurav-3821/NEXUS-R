export function UserProfileCard() {
  const handleAuthClick = () => {
    alert("Authentication system coming soon");
  };

  return (
    <div className="flex items-center gap-2.5 px-2 py-1.5 border border-gray-200 dark:border-slate-800 rounded-2xl shadow-sm bg-white dark:bg-slate-900 transition-colors">
      <img 
        src="https://ui-avatars.com/api/?name=Gaurav+Tayde&background=111827&color=fff" 
        alt="User" 
        className="w-8 h-8 rounded-full shrink-0"
      />
      <span className="text-sm font-semibold text-gray-900 dark:text-gray-100 truncate flex-1">
        Gaurav Tayde
      </span>

    </div>
  );
}
