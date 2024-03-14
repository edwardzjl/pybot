import { useCallback, useEffect, useState } from 'react';

const Collapsible = ({ openText, closeText, children, className }) => {
    const [open, setOpen] = useState(false);
    const [text, setText] = useState(closeText);
    const toggleOpen = useCallback(() => {
        setOpen((open) => !open);
    }, []);

    useEffect(() => {
        setText(open ? openText : closeText);
    }, [open, openText, closeText]);

    return (
        <>
            <button className={className} onClick={toggleOpen}>{text}</button>
            {open && children}
        </>
    );
};

export default Collapsible;
