// file: index.js

const SERVER = "http://delphi:2100";

//--------------------------------------------------------------------------------------------------
// map

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
    setOverlayParams(params) {
      overlay.setUrl(`${SERVER}/render?${params}`);
    },
  }
}

//--------------------------------------------------------------------------------------------------
// Config selector (LHS bar)

function initConfigSelector(parameters, updateSelection) {
  const container = document.getElementById('parameters');
  const inputWidgets = parameters.map(parameterInputWidget);

  function currentSelection() {
    return Object.fromEntries(
      inputWidgets.map((widget) => [widget.name, widget.value])
    );
  }

  function onsubmit() {
    updateSelection(currentSelection());
    return false;
  }

  function idToLabel(id) {
    return id
      .toLowerCase()
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (m) => m[0].toUpperCase());
  }

  function parameterInputWidget(param, setValue) {
    if (param.type == "int" || param.type == "float") {
      return node(
        'input',
        {
          name: param.id,
          type: "number",
          value: param.defaultValue,
          step: param.type == "int" ? 1 : 0.01,
        },
      );
    } else if (param.type == "select") {
      return node(
        "select",
        {name: param.id},
        ...param.options.map((option) => node(
          'option',
          {value: option, selected: option == param.defaultValue},
          idToLabel(option),
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
      ...parameters.map((param, index) => 
        node(
          'fieldset',
          {},
          node('legend', {}, idToLabel(param.id)),
          inputWidgets[index],
        )
      ),
      node('input', {type: 'submit', value: 'Apply'}),
      throbber,
    )
  );

  return {
    initialSelection: currentSelection(),
    onStartingLoading() {
      throbber.classList.remove('hidden');
    },
    onFinishedLoading() {
      throbber.classList.add('hidden');
    },
  };
}

//--------------------------------------------------------------------------------------------------
// histogram

function initHistogram() {
  const container = document.getElementById('histogram');
  const image = node('img', {
    onError() {
      if (image.src != 'about:blank') {
        image.src = 'about:blank';
      }
    },
  })
  container.append(image)

  return {
    setHistogramParams(params) {
      image.src = `${SERVER}/histogram?${params}`;
    },
  };
}

//--------------------------------------------------------------------------------------------------
// utils

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

//--------------------------------------------------------------------------------------------------
// main

function main(config) {
  const selection = {};
  function updateSelection(newValues) {
    Object.assign(selection, newValues);
    applySelection();
  }

  let loading = false;
  let nextParams = null;
  function applySelection() {
    const params = new URLSearchParams(selection);
    if (loading) {
      nextParams = params;
    } else {
      loading = true;
      onStartingLoading();
      setOverlayParams(params);
      setHistogramParams(params);
    }
  }

  function onOverlayLoaded() {
    if (nextParams) {
      setOverlayParams(nextParams);
      setHistogramParams(nextParams);
      nextParams = null;
    } else {
      loading = false;
      onFinishedLoading();
    }
  }

  const {
    initialSelection: initialMapSelection,
    setOverlayParams,
  } = initMap(updateSelection, onOverlayLoaded);

  const {
    initialSelection: initialConfigSelection,
    onStartingLoading,
    onFinishedLoading,
  } = initConfigSelector(config.parameters, updateSelection);

  const {
    setHistogramParams,
  } = initHistogram();

  Object.assign(selection, initialMapSelection, initialConfigSelection);
  applySelection();
}


window.onload = () => {
  fetch('/config')
    .then((response) => response.json())
    .then((config) => main(config))
};

//--------------------------------------------------------------------------------------------------
