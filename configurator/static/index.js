// file: index.js

const PARAMETERS = [
  {
    id: "kernel_radius_metres", 
    type: "int",
    defaultValue: 750,
  },
  {
    id: "gradient",
    type: "select",
    options: ["GREEN_TO_RED"],
    defaultValue: "GREEN_TO_RED",
  },
  {
    id: "num_colors",
    type: "int",
    defaultValue: 200,
  },
];


function initMap(updateSelection, onOverlayLoaded) {
  const map = new L.map('map', {
    center: [55.9412, -3.1915],
    zoom: 14,
    minZoom: 12,
    maxZoom: 15
  });

  // L.tileLayer(
  //   'https://cartodb-basemaps-{s}.global.ssl.fastly.net/light_all/{z}/{x}/{y}.png/',
  //   zIndex: 1,
  // ).addTo(map);

  let bounds = map.getBounds();
  const overlay = L.imageOverlay(
    'about:blank',
    bounds,
    {zIndex: 2},
  ).addTo(map);
  overlay.on('load', () => {
    overlay.setBounds(bounds);
    onOverlayLoaded();
  })

  L.tileLayer(
    'http://delphi:8000/maps/base-tiles/saintamh.jhcipa67/{z}/{x}/{y}.png',
    {
      zIndex: 3,
      pane: 'overlayPane',
    },
  ).addTo(map);

  function currentSelection() {
    bounds = map.getBounds();
    return {
      west: bounds.getWest(),
      south: bounds.getSouth(),
      east: bounds.getEast(),
      north: bounds.getNorth(),
      zoom: map.getZoom(),
    };
  };

  map.on('zoomend', () => updateSelection(currentSelection()))
  map.on('moveend', () => updateSelection(currentSelection()))

  return {
    initialSelection: currentSelection(),
    setOverlayUrl: (url) => {
      overlay.setUrl(url);
    },
  }
}


function initConfig(updateSelection) {
  const container = document.getElementById('parameters');
  const inputWidgets = PARAMETERS.map(parameterInputWidget);

  function currentSelection() {
    return Object.fromEntries(
      inputWidgets.map((widget) => [widget.name, widget.value])
    );
  }

  function onsubmit() {
    updateSelection(currentSelection());
    return false;
  }

  function parameterInputWidget(param, setValue) {
    if (param.type == "int") {
      return node(
        'input',
        {
          name: param.id,
          type: "number",
          value: param.defaultValue,
        },
      );
    } else if (param.type == "select") {
      return node(
        "select",
        {name: param.id},
        ...param.options.map((option) => node(
          'option',
          {value: option, selected: option == param.defaultValue},
          option
        ))
      );
    } else {
      return param.id;
    }
  }

  const throbber = node('p', {'className': 'hidden'}, 'Loading...');

  container.append(
    node(
      'form',
      { onsubmit },
      ...PARAMETERS.map((param, index) => 
        node(
          'fieldset',
          {},
          node('legend', {}, param.id),
          inputWidgets[index],
        )
      ),
      node('input', {type: 'submit', value: 'Apply'}),
      throbber,
    )
  );

  return {
    initialSelection: currentSelection(),
    onStartingLoading: () => {
      throbber.classList.remove('hidden');
    },
    onFinishedLoading: () => {
      throbber.classList.add('hidden');
    },
  };
}


function node(tagName, attributes={}, ...children) {
  const element = document.createElement(tagName);
  for (const [key, value] of Object.entries(attributes)) {
    element[key] = value;
  }
  for (const child of children) {
    element.append(child);
  }
  return element;
}


function main() {
  const selection = {};
  function updateSelection(newValues) {
    Object.assign(selection, newValues);
    applySelection();
  }

  let loading = false;
  let nextUrl = null;
  function applySelection() {
    const url = 'http://delphi:2100/render?' + new URLSearchParams(selection);
    if (loading) {
      nextUrl = url;
    } else {
      loading = true;
      onStartingLoading();
      setOverlayUrl(url);
    }
  }

  function onOverlayLoaded() {
    if (nextUrl) {
      setOverlayUrl(nextUrl);
      nextUrl = null;
    } else {
      loading = false;
      onFinishedLoading();
    }
  }

  const {
    initialSelection: initialMapSelection,
    setOverlayUrl,
  } = initMap(updateSelection, onOverlayLoaded);
  const {
    initialSelection: initialConfigSelection,
    onStartingLoading,
    onFinishedLoading,
  } = initConfig(updateSelection);

  Object.assign(selection, initialMapSelection, initialConfigSelection);
  applySelection();
}


window.onload = main;
