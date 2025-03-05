'use client';

import React from "react";
import { Model } from "@/model";
import { fileSelectController } from "@/controllers";

export default function Home() {
    const [model, setModel] = React.useState(new Model())
    const [redraw, forceRedraw] = React.useState(0);

    function refresh() {
        forceRedraw(redraw + 1);
    }

    function handleFileSelect(event: any) {
        fileSelectController(model, event.target.files[0], refresh)
    }

    return (
        <div>
            <input type="file" onChange={handleFileSelect}/>
        </div>
    )

}